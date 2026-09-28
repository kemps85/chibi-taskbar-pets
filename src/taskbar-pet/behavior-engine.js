import { MovementController, DIRECTIONS, createXorshift32 } from "./movement.js";

/**
 * Create a function-shaped deterministic default random dependency. Production
 * hosts should inject a session-seeded stream and persist its state.
 * @returns {() => number} random float source
 */
function createDefaultRng() {
  const stream = createXorshift32();
  return () => stream.nextFloat01();
}

/**
 * Behavior engine for a taskbar character. It owns only deterministic
 * decisions and needs state; rendering and asset playback remain external.
 */
export class BehaviorEngine {
  /**
   * @param {object} options engine dependencies and data
   * @param {string} options.character character identifier exposed in snapshots
   * @param {object} options.config data-driven needs, actions, timing, and movement configuration
   * @param {() => number} [options.rng] injected random source in [0, 1)
   * @param {() => number} [options.clock] injected monotonic millisecond clock
   * @param {{hunger?: number, sleepiness?: number}} [options.initialNeeds] initial normalized need values
   * @param {number} [options.initialAnchorX=0] initial horizontal anchor
   * @param {"left"|"right"} [options.initialDirection="right"] initial facing direction
   */
  constructor({
    character,
    config = {},
    rng = createDefaultRng(),
    clock = defaultMonotonicClock,
    initialNeeds = {},
    initialAnchorX,
    initialDirection = DIRECTIONS.RIGHT,
  }) {
    if (typeof character !== "string" || character.length === 0) {
      throw new TypeError("character must be a non-empty string");
    }
    if (typeof clock !== "function" && !(clock && typeof clock.now === "function")) {
      throw new TypeError("clock must be a function or expose now");
    }

    this.character = character;
    this.config = normalizeConfig(config, character);
    this.rng = normalizeRandomSource(rng);
    this.clock = typeof clock === "function" ? clock : () => clock.now();
    this.needs = {
      hunger: clampNeed(initialNeeds.hunger ?? 0),
      sleepiness: clampNeed(initialNeeds.sleepiness ?? 0),
    };
    this.movement = new MovementController({
      anchorX: initialAnchorX ?? this.config.movement.initialAnchorX,
      workArea: this.config.movement.workArea,
      minDistance: this.config.movement.minDistance,
      maxDistance: this.config.movement.maxDistance,
      speedPxPerSecond: this.config.movement.speedPxPerSecond,
      edgeInset: this.config.movement.edgeInset,
      rng: this.rng,
      direction: initialDirection,
    });

    this.action = null;
    this.state = "idle";
    this.deadline = null;
    this.lastAction = null;
    this.recentActions = [];
    this.cooldowns = new Map();
    this.lastNeedsAt = null;
    this.lastTickAt = null;
    this.nextDecisionAt = null;
    this.pendingFeed = false;
  }

  /**
   * Advance needs and behavior using an injected monotonic timestamp.
   * @param {number} [nowMs] current monotonic time in milliseconds
   * @returns {BehaviorSnapshot} current public overlay snapshot
   */
  tick(nowMs = this.clock()) {
    const now = assertTime(nowMs);
    const elapsedNeedsMs = this.advanceNeeds(now);
    const elapsedTickMs = this.lastTickAt === null ? 0 : Math.max(0, now - this.lastTickAt);
    this.lastTickAt = Math.max(this.lastTickAt ?? now, now);
    if (this.action === "walk") {
      this.movement.update(elapsedTickMs);
    }

    if (this._processDueAction(now)) {
      return this.snapshot(now);
    }
    if (!this.action && this.pendingFeed) {
      this._applyFeed(now);
      return this.snapshot(now);
    }
    if (this._ensureUrgentAction(now)) {
      return this.snapshot(now);
    }
    if (!this.action && (this.nextDecisionAt === null || now >= this.nextDecisionAt)) {
      this.chooseAction(now);
    }
    // Avoid an unused local while keeping elapsed needs behavior explicit in
    // the source: movement and action deadlines use the same real-time tick.
    void elapsedNeedsMs;
    return this.snapshot(now);
  }

  /**
   * Alias for integrations that call the engine once per frame.
   * @param {number} [nowMs] current monotonic time in milliseconds
   * @returns {BehaviorSnapshot} current public overlay snapshot
   */
  update(nowMs = this.clock()) {
    return this.tick(nowMs);
  }

  /**
   * Choose one ordinary weighted action from the currently eligible actions.
   * @param {number} [nowMs] current monotonic time in milliseconds
   * @returns {BehaviorSnapshot} snapshot after choosing an action
   */
  chooseAction(nowMs = this.clock()) {
    const now = assertTime(nowMs);
    this.advanceNeeds(now);
    if (this._ensureUrgentAction(now)) {
      return this.snapshot(now);
    }
    const eligible = this._eligibleOrdinaryActions(now);
    if (eligible.length === 0) {
      return this.snapshot(now);
    }
    const selected = weightedChoice(eligible, this.rng);
    if (selected.id === this.config.sleep.sleepAction && selected.isSleepRequest) {
      this.beginAction(this.config.sleep.cueAction, now, { forced: true });
    } else {
      this.beginAction(selected.id, now);
    }
    return this.snapshot(now);
  }

  /**
   * Feed the character, resetting hunger and cancelling an active notice.
   * @param {number} [nowMs] current monotonic time in milliseconds
   * @returns {BehaviorSnapshot} snapshot after feeding
   */
  feed(nowMs = this.clock()) {
    const now = assertTime(nowMs);
    this.advanceNeeds(now);
    const activeDefinition = this.config.actions[this.action];
    const sleepActions = new Set([
      this.config.sleep.cueAction,
      this.config.sleep.enterAction,
      this.config.sleep.sleepAction,
      this.config.sleep.wakeAction,
    ]);
    if (sleepActions.has(this.action) || activeDefinition?.atomic) {
      this.pendingFeed = true;
      return this.snapshot(now);
    }
    this._applyFeed(now);
    return this.snapshot(now);
  }

  /**
   * Wake the character immediately when an external command requires it.
   * @param {number} [nowMs] current monotonic time in milliseconds
   * @returns {BehaviorSnapshot} snapshot after waking
   */
  wake(nowMs = this.clock()) {
    const now = assertTime(nowMs);
    this.advanceNeeds(now);
    this.needs.sleepiness = this.config.sleep.valueAfterWake;
    this.action = null;
    this.state = "idle";
    this.deadline = null;
    this.nextDecisionAt = now;
    return this.snapshot(now);
  }

  /**
   * Execute a small public command surface for UI or host integration.
   * @param {string|{type: string, nowMs?: number}} command command name or payload
   * @param {number} [nowMs] command timestamp when command is a string
   * @returns {BehaviorSnapshot} resulting snapshot
   */
  command(command, nowMs) {
    const type = typeof command === "string" ? command : command?.type;
    const time = typeof command === "string" ? nowMs : command?.nowMs;
    if (type === "feed") {
      return this.feed(time ?? this.clock());
    }
    if (type === "wake") {
      return this.wake(time ?? this.clock());
    }
    if (type === "tick" || type === "update") {
      return this.tick(time ?? this.clock());
    }
    throw new RangeError(`Unknown behavior command: ${type}`);
  }

  /**
   * Read a snapshot while synchronizing needs to the supplied time. This does
   * not start a new action, which keeps inspection side-effect predictable.
   * @param {number} [nowMs] current monotonic time in milliseconds
   * @returns {BehaviorSnapshot} public state snapshot
   */
  snapshot(nowMs = this.clock()) {
    const now = assertTime(nowMs);
    this.advanceNeeds(now);
    const movement = this.movement.snapshot();
    return {
      character: this.character,
      state: this.state,
      action: this.action ?? "idle",
      direction: movement.direction,
      anchorX: movement.anchorX,
      needs: {
        hunger: this.needs.hunger,
        sleepiness: this.needs.sleepiness,
        hungerUrgent: this.isHungerUrgent(),
        sleepUrgent: this.isSleepUrgent(),
      },
      deadline: this.deadline,
      remainingMs: this.deadline === null ? null : Math.max(0, this.deadline - now),
    };
  }

  /**
   * Advance need meters by elapsed monotonic time.
   * @param {number} nowMs current monotonic time in milliseconds
   * @returns {number} elapsed milliseconds applied
   */
  advanceNeeds(nowMs) {
    const now = assertTime(nowMs);
    if (this.lastNeedsAt === null) {
      this.lastNeedsAt = now;
      return 0;
    }
    const elapsedMs = Math.max(0, now - this.lastNeedsAt);
    this.lastNeedsAt = Math.max(this.lastNeedsAt, now);
    const elapsedSeconds = elapsedMs / 1000;
    this.needs.hunger = clampNeed(
      this.needs.hunger + this.config.needs.hunger.ratePerSecond * elapsedSeconds,
    );
    const isAsleep = this.action === this.config.sleep.sleepAction;
    const sleepRate = isAsleep && !this.config.needs.sleepiness.accruesWhileSleeping
      ? 0
      : this.config.needs.sleepiness.ratePerSecond;
    this.needs.sleepiness = clampNeed(this.needs.sleepiness + sleepRate * elapsedSeconds);
    return elapsedMs;
  }

  /**
   * Return whether hunger is at its configured urgent threshold.
   * @returns {boolean} true when hungry notice should take priority
   */
  isHungerUrgent() {
    return this.needs.hunger >= this.config.needs.hunger.urgentAt;
  }

  /**
   * Return whether sleepiness is at its configured urgent threshold.
   * @returns {boolean} true when sleep sequence should take priority
   */
  isSleepUrgent() {
    return this.needs.sleepiness >= this.config.needs.sleepiness.forcedAt;
  }

  /**
   * Begin an action and apply its configured cooldown.
   * @param {string} actionId action identifier
   * @param {number} nowMs current monotonic time in milliseconds
   * @param {{forced?: boolean, durationMs?: number}} [options] transition options
   * @returns {void}
   */
  beginAction(actionId, nowMs, { forced = false, durationMs } = {}) {
    const action = this.config.actions[actionId] ?? { weight: 0, durationMs: 0, cooldownMs: 0 };
    const now = assertTime(nowMs);
    if (this.action) {
      this.recentActions = [this.action, ...this.recentActions]
        .filter((id, index, ids) => ids.indexOf(id) === index)
        .slice(0, this.config.recentHistoryLength);
      this.lastAction = this.action;
    }
    this.action = actionId;
    this.state = actionId;
    let duration = durationMs
      ?? (action.durationRange
        ? randomBetween(action.durationRange.minimum, action.durationRange.maximum, this.rng)
        : (actionId === "pause" && this.config.movement.pauseDurationRange
          ? randomBetween(this.config.movement.pauseDurationRange.minimum, this.config.movement.pauseDurationRange.maximum, this.rng)
          : action.durationMs));
    this.nextDecisionAt = null;
    if (!forced || action.cooldownMs > 0) {
      this.cooldowns.set(actionId, now + action.cooldownMs);
    }

    if (actionId === "walk") {
      const targetX = this.movement.startWalk();
      if (duration <= 0 && this.config.movement.speedPxPerSecond > 0) {
        duration = Math.round(Math.abs(targetX - this.movement.anchorX)
          / this.config.movement.speedPxPerSecond * 1000);
      }
    } else {
      this.movement.setAnchorX(this.movement.anchorX);
    }
    this.deadline = duration > 0 ? now + duration : null;
  }

  /**
   * Finish the current action and enter idle without selecting a replacement.
   * @param {number} nowMs current monotonic time in milliseconds
   * @returns {void}
   */
  finishAction(nowMs) {
    if (this.action) {
      this.recentActions = [this.action, ...this.recentActions]
        .filter((id, index, ids) => ids.indexOf(id) === index)
        .slice(0, this.config.recentHistoryLength);
    }
    this.lastAction = this.action;
    this.action = null;
    this.state = "idle";
    this.deadline = null;
    this.nextDecisionAt = nowMs + this.config.decisionIntervalMs;
  }

  /**
   * Process one expired action deadline. Returning true means a phase changed
   * and the caller should expose that phase before processing another one.
   * @param {number} nowMs current monotonic time in milliseconds
   * @returns {boolean} whether a deadline transition occurred
   */
  _processDueAction(nowMs) {
    if (!this.action || (this.deadline !== null && nowMs < this.deadline)) {
      return false;
    }
    const action = this.action;
    const sleepActions = new Set([
      this.config.sleep.cueAction,
      this.config.sleep.enterAction,
      this.config.sleep.sleepAction,
      this.config.sleep.wakeAction,
    ]);
    if (this.pendingFeed && !this.config.actions[action]?.atomic && !sleepActions.has(action)) {
      this._applyFeed(nowMs);
      return true;
    }
    if (action === this.config.sleep.cueAction) {
      this.beginAction(this.config.sleep.enterAction, nowMs, { forced: true });
      return true;
    }
    if (action === this.config.sleep.enterAction) {
      const duration = randomBetween(
        this.config.sleep.minDurationMs,
        this.config.sleep.maxDurationMs,
        this.rng,
      );
      this.beginAction(this.config.sleep.sleepAction, nowMs, { forced: true, durationMs: duration });
      return true;
    }
    if (action === this.config.sleep.sleepAction) {
      this.needs.sleepiness = this.config.sleep.valueAfterWake;
      this.beginAction(this.config.sleep.wakeAction, nowMs, { forced: true });
      return true;
    }
    if (action === this.config.sleep.wakeAction) {
      this.needs.sleepiness = this.config.sleep.valueAfterWake;
      this.finishAction(nowMs);
      return false;
    }
    this.finishAction(nowMs);
    return false;
  }

  /**
   * Apply a feed signal at a safe action boundary and optionally play the
   * authored eat one-shot before returning to ordinary scheduling.
   * @param {number} nowMs current monotonic time in milliseconds
   * @returns {void}
   */
  _applyFeed(nowMs) {
    this.pendingFeed = false;
    this.needs.hunger = 0;
    const noticeAction = this.config.hunger.noticeAction;
    if (this.action === noticeAction) {
      this.finishAction(nowMs);
    }
    this.cooldowns.delete(noticeAction);
    if (this.config.actions.eat) {
      this.beginAction("eat", nowMs, { forced: true });
    } else {
      this.nextDecisionAt = nowMs;
    }
  }

  /**
   * Promote urgent sleep or hunger notice over ordinary actions.
   * @param {number} nowMs current monotonic time in milliseconds
   * @returns {boolean} whether an urgent action is active or was started
   */
  _ensureUrgentAction(nowMs) {
    const sleepActions = new Set([
      this.config.sleep.cueAction,
      this.config.sleep.enterAction,
      this.config.sleep.sleepAction,
      this.config.sleep.wakeAction,
    ]);
    if (sleepActions.has(this.action)) {
      return true;
    }
    if (this.isSleepUrgent()) {
      const currentDefinition = this.config.actions[this.action];
      if (currentDefinition?.atomic && this.deadline !== null && nowMs < this.deadline) {
        return true;
      }
      this.beginAction(this.config.sleep.cueAction, nowMs, { forced: true });
      return true;
    }
    if (this.action === this.config.hunger.noticeAction) {
      return true;
    }
    if (this.isHungerUrgent()) {
      const cooldownUntil = this.cooldowns.get(this.config.hunger.noticeAction) ?? 0;
      if (nowMs >= cooldownUntil) {
        this.beginAction(this.config.hunger.noticeAction, nowMs, { forced: true });
        const urgency = (this.needs.hunger - this.config.needs.hunger.urgentAt)
          / Math.max(0.000001, 1 - this.config.needs.hunger.urgentAt);
        const repeatMs = this.config.hunger.repeatAtThresholdMs
          + (this.config.hunger.repeatAtMaximumMs - this.config.hunger.repeatAtThresholdMs)
            * Math.min(1, Math.max(0, urgency));
        this.cooldowns.set(this.config.hunger.noticeAction, nowMs + Math.round(repeatMs));
        return true;
      }
      return false;
    }
    return false;
  }

  /**
   * Build eligible ordinary actions with cooldown and repeat rules applied.
   * @param {number} nowMs current monotonic time in milliseconds
   * @returns {Array<{id: string, weight: number}>} eligible weighted actions
   */
  _eligibleOrdinaryActions(nowMs) {
    const hungerThreshold = this.config.needs.hunger.urgentAt;
    const hungerUrgency = this.needs.hunger <= hungerThreshold
      ? 0
      : (this.needs.hunger - hungerThreshold) / Math.max(0.000001, 1 - hungerThreshold);
    const hungerMultiplier = 1 - Math.min(1, Math.max(0, hungerUrgency))
      * (1 - this.config.hunger.ordinaryActionMultiplierAtMaximum);
    const candidates = this.config.ordinaryActions
      .map((id) => ({ id, ...this.config.actions[id] }))
      .filter((action) => action.weight > 0 && nowMs >= (this.cooldowns.get(action.id) ?? 0))
      .map((action) => ({ ...action, weight: action.weight * hungerMultiplier }));
    if (
      this.needs.sleepiness >= this.config.needs.sleepiness.eligibleAt
      && !this.isSleepUrgent()
      && nowMs >= (this.cooldowns.get(this.config.sleep.sleepAction) ?? 0)
    ) {
      const urgency = (this.needs.sleepiness - this.config.needs.sleepiness.eligibleAt)
        / Math.max(0.000001, this.config.needs.sleepiness.forcedAt - this.config.needs.sleepiness.eligibleAt);
      candidates.push({
        id: this.config.sleep.sleepAction,
        weight: this.config.sleep.baseWeight + this.config.sleep.urgencyWeightGain * Math.min(1, Math.max(0, urgency)),
        isSleepRequest: true,
      });
    }
    if (candidates.length <= 1 || this.lastAction === null) {
      return candidates;
    }
    if (this.config.immediateRepeat.exclude) {
      const withoutRepeat = candidates.filter((action) => action.id !== this.lastAction);
      if (withoutRepeat.length > 0) {
        return withoutRepeat;
      }
    }
    return candidates.map((action) => ({
      ...action,
      weight: action.weight * repeatMultiplier(action.id, this.lastAction, this.recentActions, this.config),
    }));
  }
}

/**
 * Create a behavior engine through a named factory for host integrations.
 * @param {ConstructorParameters<typeof BehaviorEngine>[0]} options engine options
 * @returns {BehaviorEngine} configured engine
 */
export function createBehaviorEngine(options) {
  return new BehaviorEngine(options);
}

/**
 * Calculate the recent-action multiplier for a candidate.
 * @param {string} actionId candidate action
 * @param {string|null} immediate previous action
 * @param {readonly string[]} recentActions prior action history
 * @param {{immediateRepeat: {penalty: number, recentPenalty: number}}} config repeat tuning
 * @returns {number} weight multiplier
 */
function repeatMultiplier(actionId, immediate, recentActions, config) {
  if (actionId === immediate) {
    return config.immediateRepeat.penalty;
  }
  return recentActions.includes(actionId) ? config.immediateRepeat.recentPenalty : 1;
}

/**
 * Snapshot shape exposed to the overlay host.
 * @typedef {{character: string, state: string, action: string, direction: "left"|"right", anchorX: number, needs: {hunger: number, sleepiness: number, hungerUrgent: boolean, sleepUrgent: boolean}, deadline: number|null, remainingMs: number|null}} BehaviorSnapshot
 */

/**
 * Normalize data-driven behavior configuration and apply only structural
 * defaults, leaving character tuning in the injected config.
 * @param {object} config raw behavior configuration
 * @returns {object} normalized configuration
 */
function normalizeConfig(config, character) {
  if (!config || typeof config !== "object") {
    throw new TypeError("config must be an object");
  }
  const characterConfig = config.characters?.[character] ?? {};
  const actionSource = config.actions ?? characterConfig.actions ?? {};
  const actions = {};
  if (Array.isArray(actionSource)) {
    for (const action of actionSource) {
      if (action?.id) {
        actions[action.id] = normalizeAction(action);
      }
    }
  } else {
    for (const [id, action] of Object.entries(actionSource)) {
      actions[id] = normalizeAction(action);
    }
  }
  for (const id of ["walk", "pause", "signature"]) {
    actions[id] ??= normalizeAction({ weight: id === "pause" ? 1 : 0, durationMs: 0 });
  }
  const hunger = config.hunger ?? config.needs?.hunger ?? {};
  const sleep = config.sleep ?? config.needs?.sleepiness ?? {};
  const needs = config.needs ?? {};
  const hungerNeeds = needs.hunger ?? {};
  const sleepNeeds = needs.sleepiness ?? {};
  const noticeAction = hunger.noticeAction ?? "hungry_notice";
  const cueAction = sleep.cueAction ?? "sleep_cue";
  const enterAction = sleep.enterAction ?? "sleep_enter";
  const sleepAction = sleep.sleepAction
    ?? (sleep.sequence?.some((phase) => String(phase).startsWith("sleep_loop")) ? "sleep_loop" : "sleep");
  const wakeAction = sleep.wakeAction ?? "wake";
  actions[noticeAction] ??= normalizeAction({ durationMs: hunger.noticeDurationMs ?? hunger.cueVisibleMs ?? 0, cooldownMs: hunger.noticeCooldownMs ?? hunger.cueRepeatMsAtThreshold ?? 0 });
  actions[cueAction] ??= normalizeAction({ durationMs: sleep.cueDurationMs ?? 0, cooldownMs: 0 });
  actions[enterAction] ??= normalizeAction({ durationMs: sleep.enterDurationMs ?? 0, cooldownMs: 0 });
  actions[sleepAction] ??= normalizeAction({ durationMs: 0, cooldownMs: 0 });
  actions[wakeAction] ??= normalizeAction({ durationMs: sleep.wakeDurationMs ?? 0, cooldownMs: 0 });

  const ordinaryActions = config.ordinaryActions
    ?? characterConfig.ordinaryActions
    ?? (Array.isArray(characterConfig.actions)
      ? characterConfig.actions.map((action) => action.id).filter((id) => actions[id]?.weight > 0)
      : ["walk", "pause", "signature"].filter((id) => actions[id].weight > 0));
  return {
    decisionIntervalMs: nonNegative(config.decisionIntervalMs ?? 0),
    recentHistoryLength: Math.max(1, Math.floor(nonNegative(config.recentHistoryLength ?? config.scheduler?.recentHistoryLength ?? 3))),
    immediateRepeat: {
      exclude: Boolean(config.immediateRepeat?.exclude ?? config.excludeImmediateRepeat ?? false),
      penalty: clampUnit(config.immediateRepeat?.penalty ?? config.immediateRepeatPenalty ?? config.scheduler?.repeatPenalty?.immediateMultiplier ?? 0.1),
      recentPenalty: clampUnit(config.immediateRepeat?.recentPenalty ?? config.scheduler?.repeatPenalty?.recentMultiplier ?? 0.5),
    },
    ordinaryActions: [...ordinaryActions],
    actions,
    needs: {
      hunger: normalizeNeed(hungerNeeds, hunger),
      sleepiness: normalizeNeed(sleepNeeds, sleep),
    },
    hunger: {
      noticeAction,
      repeatAtThresholdMs: nonNegative(hunger.cueRepeatMsAtThreshold ?? 20000),
      repeatAtMaximumMs: nonNegative(hunger.cueRepeatMsAtMaximum ?? hunger.cueRepeatMsAtThreshold ?? 8000),
      ordinaryActionMultiplierAtMaximum: clampUnit(config.scheduler?.ordinaryActionHungerMultiplierAtMaximum ?? hunger.ordinaryActionMultiplierAtMaximum ?? 0.5),
    },
    sleep: {
      cueAction,
      enterAction,
      sleepAction,
      wakeAction,
      minDurationMs: nonNegative(sleep.minDurationMs ?? sleep.durationMinMs ?? sleep.sleepLoopDurationMs?.minimum ?? 480000),
      maxDurationMs: nonNegative(sleep.maxDurationMs ?? sleep.durationMaxMs ?? sleep.sleepLoopDurationMs?.maximum ?? 720000),
      eligibleAt: clampNeed(sleep.eligibleAt ?? sleep.eligibleThreshold ?? sleepNeeds.eligibleAt ?? sleepNeeds.eligibleThreshold ?? 0.7),
      forcedAt: clampNeed(sleep.forcedAt ?? sleep.forcedThreshold ?? sleepNeeds.forcedAt ?? sleepNeeds.forcedThreshold ?? sleepNeeds.urgentAt ?? 0.9),
      baseWeight: nonNegative(sleep.baseWeight ?? sleep.sleepBaseWeight ?? 1),
      urgencyWeightGain: nonNegative(sleep.urgencyWeightGain ?? sleep.sleepUrgencyWeightGain ?? 8),
      valueAfterWake: clampNeed(sleep.valueAfterWake ?? sleepNeeds.valueAfterWake ?? 0.05),
    },
    movement: normalizeMovement(config.movement ?? config.locomotion),
  };
}

/**
 * Normalize one action's numeric tuning.
 * @param {object} action raw action data
 * @returns {{weight: number, durationMs: number, cooldownMs: number}} normalized action
 */
function normalizeAction(action = {}) {
  const durationRange = normalizeRange(action.loopDurationMs);
  return {
    weight: nonNegative(action.weight ?? action.baseWeight ?? 0),
    durationMs: nonNegative(action.durationMs ?? (typeof action.loopDurationMs === "number" ? action.loopDurationMs : 0)),
    cooldownMs: nonNegative(action.cooldownMs ?? 0),
    atomic: Boolean(action.atomic),
    durationRange,
  };
}

/**
 * Normalize an optional uniform duration range.
 * @param {number|{minimum?: number, maximum?: number}|undefined} range duration range
 * @returns {{minimum: number, maximum: number}|null} normalized range
 */
function normalizeRange(range) {
  if (range === undefined || range === null || typeof range === "number") {
    return null;
  }
  if (typeof range !== "object") {
    throw new TypeError("duration range must be a number or object");
  }
  const minimum = nonNegative(range.minimum ?? 0);
  const maximum = nonNegative(range.maximum ?? minimum);
  if (maximum < minimum) {
    throw new RangeError("duration range maximum must be greater than or equal to minimum");
  }
  return { minimum, maximum };
}

/**
 * Normalize a need's rate and threshold aliases.
 * @param {object} need specific need data
 * @param {object} fallback parent need data
 * @returns {{ratePerSecond: number, urgentAt: number}} normalized need
 */
function normalizeNeed(need, fallback) {
  const explicitRatePerSecond = need.ratePerSecond
    ?? need.gainPerSecond
    ?? need.rate;
  const ratePerSecond = explicitRatePerSecond
    ?? ((need.ratePerMinute ?? fallback.ratePerMinute) !== undefined
      ? (need.ratePerMinute ?? fallback.ratePerMinute) / 60
      : undefined);
  const elapsedFullAfterMs = need.fullAfterMs ?? need.fullAfterAwakeMs ?? fallback.fullAfterMs ?? fallback.fullAfterAwakeMs;
  return {
    ratePerSecond: nonNegative(ratePerSecond ?? (elapsedFullAfterMs ? 1000 / elapsedFullAfterMs : 0)),
    urgentAt: clampNeed(need.urgentAt ?? need.urgentThreshold ?? need.cueThreshold ?? fallback.urgentAt ?? fallback.urgentThreshold ?? fallback.cueThreshold ?? 1),
    eligibleAt: clampNeed(need.eligibleAt ?? need.eligibleThreshold ?? fallback.eligibleAt ?? fallback.eligibleThreshold ?? need.urgentAt ?? fallback.urgentAt ?? 1),
    forcedAt: clampNeed(need.forcedAt ?? need.forcedThreshold ?? fallback.forcedAt ?? fallback.forcedThreshold ?? need.urgentAt ?? 1),
    accruesWhileSleeping: need.accruesWhileSleeping ?? fallback.accruesWhileSleeping ?? true,
  };
}

/**
 * Normalize movement tuning.
 * @param {object} movement raw movement data
 * @returns {object} normalized movement data
 */
function normalizeMovement(movement = {}) {
  const preferredDistance = movement.preferredDistanceDip ?? {};
  return {
    workArea: movement.workArea ?? { minX: 0, maxX: 0 },
    initialAnchorX: movement.initialAnchorX ?? 0,
    minDistance: nonNegative(movement.minDistance ?? movement.targetDistanceMin ?? preferredDistance.minimum ?? 0),
    maxDistance: nonNegative(movement.maxDistance ?? movement.targetDistanceMax ?? preferredDistance.maximum ?? movement.minDistance ?? 0),
    speedPxPerSecond: nonNegative(movement.speedPxPerSecond ?? movement.speedDipPerSecond ?? movement.speed ?? 0),
    edgeInset: nonNegative(movement.edgeInset ?? movement.edgeInsetDip ?? 0),
    pauseDurationRange: normalizeRange(movement.pauseDurationMs),
  };
}

/**
 * Select a weighted item from a non-empty list.
 * @param {Array<{id: string, weight: number}>} choices weighted choices
 * @param {() => number} rng random source
 * @returns {{id: string, weight: number}} selected choice
 */
function weightedChoice(choices, rng) {
  const total = choices.reduce((sum, choice) => sum + choice.weight, 0);
  if (total <= 0) {
    throw new RangeError("weighted choices must have a positive total weight");
  }
  const roll = randomUnit(rng) * total;
  let cumulative = 0;
  for (const choice of choices) {
    cumulative += choice.weight;
    if (roll < cumulative) {
      return choice;
    }
  }
  return choices[choices.length - 1];
}

/**
 * Sample an inclusive numeric duration from a configured range.
 * @param {number} minimum minimum duration in milliseconds
 * @param {number} maximum maximum duration in milliseconds
 * @param {() => number} rng random source
 * @returns {number} integer duration in milliseconds
 */
function randomBetween(minimum, maximum, rng) {
  if (maximum < minimum) {
    throw new RangeError("sleep maximum must be greater than or equal to minimum");
  }
  return Math.round(minimum + randomUnit(rng) * (maximum - minimum));
}

/**
 * Convert an injected random source to [0, 1).
 * @param {() => number} rng random source
 * @returns {number} bounded sample
 */
function randomUnit(rng) {
  const value = Number(rng());
  if (!Number.isFinite(value)) {
    throw new TypeError("rng must return a finite number");
  }
  return Math.min(0.9999999999999999, Math.max(0, value));
}

/**
 * Accept either a function RNG or a xorshift-like stream object.
 * @param {(() => number)|{nextFloat01: () => number}} rng random dependency
 * @returns {() => number} function-shaped random source
 */
function normalizeRandomSource(rng) {
  if (typeof rng === "function") {
    return rng;
  }
  if (rng && typeof rng.nextFloat01 === "function") {
    return () => rng.nextFloat01();
  }
  throw new TypeError("rng must be a function or expose nextFloat01");
}

/**
 * Clamp normalized need values.
 * @param {number} value raw need value
 * @returns {number} normalized need value
 */
function clampNeed(value) {
  return Math.min(1, Math.max(0, Number(value)));
}

/**
 * Clamp a value to the unit range.
 * @param {number} value raw unit value
 * @returns {number} bounded unit value
 */
function clampUnit(value) {
  return Math.min(1, Math.max(0, Number(value)));
}

/**
 * Validate and normalize non-negative numbers.
 * @param {number} value candidate number
 * @returns {number} value
 */
function nonNegative(value) {
  if (!Number.isFinite(Number(value)) || Number(value) < 0) {
    throw new RangeError("value must be a non-negative finite number");
  }
  return Number(value);
}

/**
 * Validate an injected monotonic timestamp.
 * @param {number} value timestamp
 * @returns {number} timestamp
 */
function assertTime(value) {
  if (!Number.isFinite(value)) {
    throw new TypeError("time must be a finite number");
  }
  return value;
}

/**
 * Default monotonic clock for production hosts.
 * @returns {number} monotonic milliseconds
 */
function defaultMonotonicClock() {
  return performance.now();
}
