c=$1; G=assets/generated/pixel-chibi/imagegen-v1/$c
p(){ [ -f $G/raw/$1.png ] || { echo "$c $1 MISSING"; return; }; python scripts/imagegen_postprocess.py process --character $c --raw $G/raw/$1.png --reference $2 --out $G/$3 --allow all --baseline 142 > $G/raw/$1.log 2>&1; echo "$c $1 $?"; }
mkdir -p $G/idle $G/hunger $G/eat $G/sleep $G/signature
shift; for j in "$@"; do case $j in
 blink) p blink $G/idle/k1.png idle/blink_raw;; hk1) p hk1 $G/idle/k1.png hunger/hk1;; ek1) p ek1 $G/idle/k1.png eat/ek1;; ek2) p ek2 $G/eat/ek1.png eat/ek2;;
 sc1) p sc1 $G/idle/k1.png sleep/sc1;; sk0) p sk0 $G/idle/k1.png sleep/sk0;; sk1) p sk1 $G/sleep/sk0.png sleep/sk1;; sk2) p sk2 $G/sleep/sk1.png sleep/sk2;;
 sg1|sg2|sg3) p $j $G/idle/k1.png signature/$j;; esac; done
