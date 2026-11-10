use oxidd::bdd::BDDFunction;
use oxidd::util::{AllocResult, SatCountCache};
use oxidd::util::num::F64;
use oxidd::{BooleanFunction, Function, Manager, ManagerRef};
use std::collections::hash_map::RandomState;
use std::time::Instant;

// Boolean board encoding and variable order match the BuDDy/JDD adapters.
fn main() -> AllocResult<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let rows = args.iter().any(|arg| arg == "--rows");
    let mut args = args.into_iter().filter(|arg| arg != "--rows");
    let n: usize = args.next().expect("Usage: nqueens N [workers]").parse().expect("Invalid N");
    assert!(n > 0 && n.checked_mul(n).is_some_and(|v| v < u32::MAX as usize));
    let workers: u32 = args.next().unwrap_or_else(|| "0".into()).parse().expect("Invalid workers");
    let start = Instant::now();
    // Fixed index-manager capacity: 2^26 inner nodes and 2^20 apply-cache entries.
    let manager_ref = oxidd::bdd::new_manager(1 << 26, 1 << 20, workers);
    let cells: Vec<BDDFunction> = manager_ref.with_manager_exclusive(|manager| {
        AllocResult::from_iter(manager.add_vars((n * n) as u32).map(|v| BDDFunction::var(manager, v)))
    })?;
    let (t, f) = manager_ref.with_manager_shared(|manager| (BDDFunction::t(manager), BDDFunction::f(manager)));
    let queens = if rows {
        solve_rows(n, &cells, &t, &f)?
    } else {
        let mut queens = t.clone();
        for i in 0..n {
            let mut occupied = f.clone();
            for j in 0..n {
                occupied = occupied.or(&cells[i * n + j])?;
            }
            queens = queens.and(&occupied)?;
        }
        for i in 0..n {
            for j in 0..n {
                let cell = &cells[i * n + j];
                let mut column = t.clone();
                let mut row = t.clone();
                let mut up = t.clone();
                let mut down = t.clone();
                for k in 0..n {
                    if k != j {
                        column = column.and(&cell.imp(&cells[i * n + k].not()?)?)?;
                    }
                }
                for k in 0..n {
                    if k == i { continue; }
                    row = row.and(&cell.imp(&cells[k * n + j].not()?)?)?;
                    let diagonal = k as isize - i as isize + j as isize;
                    if (0..n as isize).contains(&diagonal) {
                        up = up.and(&cell.imp(&cells[k * n + diagonal as usize].not()?)?)?;
                    }
                    let diagonal = i as isize + j as isize - k as isize;
                    if (0..n as isize).contains(&diagonal) {
                        down = down.and(&cell.imp(&cells[k * n + diagonal as usize].not()?)?)?;
                    }
                }
                queens = queens.and(&column.and(&row.and(&up.and(&down)?)?)?)?;
            }
        }
        queens
    };
    let mut cache = SatCountCache::<F64, RandomState>::default();
    let solutions = queens.sat_count((n * n) as u32, &mut cache).0;
    let nodes = queens.node_count();
    println!("NQUEENS_METRICS n={n} solutions={solutions:.0} nodes_alive={nodes} seconds={:.9}",
             start.elapsed().as_secs_f64());
    Ok(())
}

// Adapted from SSoelvsten/bdd-benchmark, commit 3c521e1 (MIT).
fn solve_rows(n: usize, cells: &[BDDFunction], t: &BDDFunction, f: &BDDFunction) -> AllocResult<BDDFunction> {
    let mut board = t.clone();
    for i in 0..n {
        let mut row = f.clone();
        for j in 0..n {
            let mut placement = t.clone();
            for v in (0..n * n).rev() {
                let (r, c) = (v / n, v % n);
                if r == i && c == j {
                    placement = cells[v].ite(&placement, f)?;
                } else if r == i || c == j || r.abs_diff(i) == c.abs_diff(j) {
                    placement = cells[v].ite(f, &placement)?;
                }
            }
            row = row.or(&placement)?;
        }
        board = board.and(&row)?;
    }
    Ok(board)
}
