#!/bin/bash
OUT=~/Smithsonian_F26/model_A/detector_v2/runs/dv2_2xl_focus_20261119
L=$OUT/watch.log
echo "$(date) watcher start; last.ckpt mtime $(date -r $OUT/last.ckpt)" >> $L
T0=$(stat -c %Y $OUT/last.ckpt)
while [ "$(stat -c %Y $OUT/last.ckpt)" = "$T0" ]; do sleep 20; done
echo "$(date) last.ckpt updated; waiting for checkpoint writes to settle" >> $L
sleep 120
while [ -n "$(find $OUT -maxdepth 1 \( -name '*.ckpt' -o -name '*.pth' \) -newermt '-30 seconds')" ]; do sleep 15; done
PID=$(pgrep -f "src.models.rfdetr.train" | head -1)
echo "$(date) stopping training pid $PID" >> $L
kill -TERM $PID
for i in $(seq 1 24); do pgrep -f "src.models.rfdetr.train" >/dev/null || break; sleep 5; done
pgrep -f "src.models.rfdetr.train" >/dev/null && { pkill -9 -f "src.models.rfdetr.train"; echo "$(date) had to SIGKILL" >> $L; }
B=$OUT/pre_resume_$(date +%Y%m%d_%H%M%S); mkdir -p $B
cp -p $OUT/metrics.csv $OUT/nohup.out $OUT/hparams.yaml $OUT/launch.log $OUT/events.out.tfevents.* $OUT/checkpoint_best_*.pth $B/ 2>/dev/null
echo "$(date) backed up logs + best checkpoints to $B" >> $L
sleep 30
/mnt/c/Windows/System32/schtasks.exe /run /tn dv2train >> $L 2>&1
echo "$(date) relaunched dv2train (resume from last.ckpt)" >> $L
