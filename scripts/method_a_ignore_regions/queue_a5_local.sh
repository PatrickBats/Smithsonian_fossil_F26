#!/bin/bash
# A5 ablations on the local GPU, run back to back after A4_cocoinit_local finishes.
# All reuse the NOTS A4 pseudo-labels and the COCO init; each stage is resumable (run_local.sh).
#   A5a  repeat-factor sampling (t=0.1)
#   A5b  A5a + rfdetr multi-scale + color jitter
#   A5c  A5b with 4,800 optimizer steps
#   A5d  class-balanced loss weights instead of RFS, + multi-scale + color jitter
cd ~/Smithsonian_F26/model_A/scripts
D=/home/alanyang/Smithsonian_F26/model_A/runs/A4_ignore_springinit_20261021_debug/data
done_() { [ -f "$1/status.json" ] && grep -q '"completed"' "$1/status.json"; }
while ! done_ ../runs/A4_cocoinit_local/eval; do sleep 60; done
date; echo "A4_cocoinit_local done, starting A5 queue"
run() { mkdir -p ../runs/$1; bash run_local.sh $1 $D "$2" >> ../runs/$1/nohup.out 2>&1; echo "$1 exit $? $(date)"; }
run A5a_rfs            "--balance rfs"
run A5b_rfs_ms_cj      "--balance rfs --multi-scale --color-jitter"
run A5c_rfs_ms_cj_4800 "--balance rfs --multi-scale --color-jitter --steps 4800"
run A5d_cb_ms_cj       "--balance cb --multi-scale --color-jitter"
echo "QUEUE DONE $(date)"
