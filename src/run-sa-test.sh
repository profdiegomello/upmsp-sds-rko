python3 -m solvers.solver-sa \
    --nome_instancia ../bench/rsdst/small/I_6_2_S_1-9_1.txt \
    --arq_saida teste.dat \
    --arq_gantt I_6_2_S_1-9_1 \
    --time_limit 45 \
    --temp_inicial 500\
    --temp_final 1 \
    --alpha 0.99 \
    --iter_por_temp 50 \
    --p_block 0.2 \
    --p_shift 0.5 \
    --block_size 3 \
    

python3 -m solvers.solver-sa \
    --nome_instancia ../bench/rsdst/small/I_10_2_S_1-49_6.txt \
    --arq_saida teste.dat \
    --arq_gantt I_10_2_S_1-49_6 \
    --time_limit 45 \
    --temp_inicial 500\
    --temp_final 1 \
    --alpha 0.99 \
    --iter_por_temp 50 \
    --p_block 0.2 \
    --p_shift 0.5 \
    --block_size 3 \
    
    
python3 -m solvers.solver-sa \
    --nome_instancia ../bench/rsdst/small/I_12_5_S_1-124_10.txt \
    --arq_saida teste.dat \
    --arq_gantt I_12_5_S_1-124_10 \
    --time_limit 45 \
    --temp_inicial 500\
    --temp_final 1 \
    --alpha 0.99 \
    --iter_por_temp 50 \
    --p_block 0.2 \
    --p_shift 0.5 \
    --block_size 3 \
    


