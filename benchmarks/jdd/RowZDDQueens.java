package benchmark.jdd;

import benchmark.common.RowQueens;
import jdd.zdd.ZDD2;

/** The row/placement algorithm with ZDD universe nodes for unconstrained bits. */
public final class RowZDDQueens extends ZDD2 {
    private RowZDDQueens(int n) {
        super(1 + Math.max(1000, (int)Math.pow(3.5, n - 6) * 1000), 10000);
        long start = System.nanoTime();
        int[] variables = new int[n * n];
        // JDD ZDD levels descend by variable ID; map them to row-major order.
        for (int v = variables.length - 1; v >= 0; v--) variables[v] = createVar();
        int root = RowQueens.solve(n, new RowQueens.Ops<Integer>() {
            public Integer one() { return ref(1); }
            public Integer zero() { return ref(0); }
            public Integer step(int v, int value, Integer tail) {
                return ref(mk(variables[v], value == 1 ? 0 : tail, value == 0 ? 0 : tail));
            }
            public Integer and(Integer a, Integer b) { return ref(intersect(a, b)); }
            public Integer or(Integer a, Integer b) { return ref(union(a, b)); }
            public void drop(Integer value) { deref(value); }
        });
        int solutions = count(root);
        double seconds = (System.nanoTime() - start) / 1e9;
        System.out.printf(java.util.Locale.ROOT,
            "NQUEENS_METRICS n=%d solutions=%d nodes_alive=%d seconds=%.9f%n",
            n, solutions, nodeCount(root), seconds);
        deref(root);
        cleanup();
    }

    public static void main(String[] args) {
        for (String arg : RowQueens.arguments(args)) new RowZDDQueens(Integer.parseInt(arg));
    }
}
