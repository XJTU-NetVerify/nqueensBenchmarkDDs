package benchmark.javabdd;

import benchmark.common.RowQueens;
import com.github.javabdd.BDD;
import com.github.javabdd.BDDFactory;
import com.github.javabdd.JFactory;
import java.math.BigInteger;
import java.util.Locale;

/** Boolean N-Queens encoding matching the repository's BuDDy and JDD adapters. */
public final class JavaBDDQueens {
    public static void main(String[] args) {
        boolean rows = RowQueens.requested(args);
        args = RowQueens.arguments(args);
        if (args.length != 1 || Integer.parseInt(args[0]) <= 0) {
            throw new IllegalArgumentException("Usage: JavaBDDQueens N (N > 0)");
        }
        int n = Integer.parseInt(args[0]);
        long start = System.nanoTime();
        // Match BuDDy's initial node table and cache sizes; allow normal growth.
        BDDFactory factory = JFactory.init(n * n * 256, 10000);
        try {
            factory.setVarNum(n * n);
            BDD[][] cells = new BDD[n][n];
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    cells[i][j] = factory.ithVar(i * n + j);
                }
            }
            BDD queens;
            if (rows) { queens = solveRows(n, cells, factory); } else {
                queens = factory.one();
                for (int i = 0; i < n; i++) {
                    BDD occupied = factory.zero();
                    for (int j = 0; j < n; j++) {
                        occupied.orWith(cells[i][j].id());
                    }
                    queens.andWith(occupied);
                }
                for (int i = 0; i < n; i++) {
                    for (int j = 0; j < n; j++) {
                        BDD column = factory.one();
                        BDD row = factory.one();
                        BDD up = factory.one();
                        BDD down = factory.one();
                        for (int k = 0; k < n; k++) {
                            if (k == j) continue;
                            exclude(column, cells[i][j], cells[i][k]);
                        }
                        for (int k = 0; k < n; k++) {
                            if (k == i) continue;
                            exclude(row, cells[i][j], cells[k][j]);
                            int diagonal = k - i + j;
                            if (diagonal >= 0 && diagonal < n) {
                                exclude(up, cells[i][j], cells[k][diagonal]);
                            }
                            diagonal = i + j - k;
                            if (diagonal >= 0 && diagonal < n) {
                                exclude(down, cells[i][j], cells[k][diagonal]);
                            }
                        }
                        up.andWith(down);
                        row.andWith(up);
                        column.andWith(row);
                        queens.andWith(column);
                    }
                }
            }
            BigInteger solutions = queens.satCount();
            int nodes = queens.nodeCount();
            double seconds = (System.nanoTime() - start) / 1e9;
            System.out.printf(Locale.ROOT,
                    "NQUEENS_METRICS n=%d solutions=%s nodes_alive=%d seconds=%.9f%n",
                    n, solutions, nodes, seconds);
            queens.free();
            for (BDD[] row : cells) {
                for (BDD cell : row) cell.free();
            }
        } finally {
            factory.done();
        }
    }


    private static BDD solveRows(int n, BDD[][] cells, BDDFactory factory) {
        return RowQueens.solve(n, new RowQueens.Ops<BDD>() {
            public BDD one() { return factory.one(); }
            public BDD zero() { return factory.zero(); }
            public BDD step(int v, int value, BDD tail) {
                if (value < 0) return tail.id();
                BDD zero = factory.zero();
                BDD result = cells[v / n][v % n].ite(value == 1 ? tail : zero, value == 0 ? tail : zero);
                zero.free();
                return result;
            }
            public BDD and(BDD a, BDD b) { return a.and(b); }
            public BDD or(BDD a, BDD b) { return a.or(b); }
            public void drop(BDD value) { value.free(); }
        });
    }

    private static void exclude(BDD constraints, BDD cell, BDD other) {
        BDD absent = other.not();
        BDD implication = cell.imp(absent);
        absent.free();
        constraints.andWith(implication);
    }
}
