grep I_100 report-rkga.dat | awk '{sum+=$9}END{ if(NR>1){ avg=(sum/NR)/60; print "ETA I_100: " avg*(200-NR) " min \tavg="avg " min" } }'
grep I_50 report-rkga.dat  | awk '{sum+=$9}END{ if(NR>1){ avg=(sum/NR)/60; print "ETA I_50:  " avg*(200-NR) " min \tavg="avg " min" } }'
