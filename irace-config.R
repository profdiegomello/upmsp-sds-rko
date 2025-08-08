parameters <- list(
  temp_inicial = list(
    type = "real",
    range = c(5, 1000)
  ),
  temp_final = list(
    type = "real",
    range = c(0.001, 1)
  ),
  alpha = list(
    type = "real",
    range = c(0.8, 0.999)
  ),
  iter_por_temp = list(
    type = "integer",
    range = c(100, 5000)
  ),
  iter_max_sa = list(
    type = "integer",
    range = c(1000, 100000)
  ),
  p_block = list(
    type = "real",
    range = c(0.01, 1)
  ),
  p_shift = list(
    type = "real",
    range = c(0.01, 1)
  ),
  block_size = list(
    type = "integer",
    range = c(1, 10)
  ),
  strategy = list(
    type = "categorical",
    values = c("block", "shift", "both")
  ),
  v_size = list(
    type = "integer",
    range = c(1, 10)
  )
)