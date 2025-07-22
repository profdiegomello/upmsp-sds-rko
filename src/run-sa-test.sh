python3 -m solvers.solver-sa \
    --nome_instancia ../bench/rsdst/small/I_6_2_S_1-9_1.txt \
    --arq_saida teste.dat \
    --arq_gantt cronograma \
    --time_limit 600 \
    --temp_inicial 100\
    --temp_final 5 \
    --alpha 0.9 \
    --iter_por_temp 15 \
    --p_block 0.2 \
    --p_shift 0.5 \
    --block_size 3 \
    --lowerbound 50
    




