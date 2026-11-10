package benchmark.common;

/** Row/placement construction adapted from SSoelvsten/bdd-benchmark at
 * 3c521e16ada406d37ae5f960096a567a41df33b9. See licenses/bdd-benchmark-MIT.txt. */
public final class RowQueens {
    private RowQueens() {}

    public static boolean requested(String[] args) {
        return java.util.Arrays.asList(args).contains("--rows");
    }

    public static String[] arguments(String[] args) {
        return java.util.Arrays.stream(args).filter(arg -> !arg.equals("--rows")).toArray(String[]::new);
    }

    /** All results are owned; operands are borrowed. step uses 1/0/-1 for
     * a positive/negative/unconstrained variable, respectively. */
    public interface Ops<T> {
        T one();
        T zero();
        T step(int variable, int value, T tail);
        T and(T a, T b);
        T or(T a, T b);
        void drop(T value);
    }

    public static <T> T solve(int n, Ops<T> ops) {
        if (n <= 0) throw new IllegalArgumentException("N must be positive");
        T board = null;
        for (int i = 0; i < n; i++) {
            T row = ops.zero();
            for (int j = 0; j < n; j++) {
                T placement = ops.one();
                for (int v = n * n - 1; v >= 0; v--) {
                    int r = v / n, c = v % n;
                    int value = r == i && c == j ? 1
                        : r == i || c == j || Math.abs(r - i) == Math.abs(c - j) ? 0 : -1;
                    T next = ops.step(v, value, placement);
                    ops.drop(placement);
                    placement = next;
                }
                T next = ops.or(row, placement);
                ops.drop(row);
                ops.drop(placement);
                row = next;
            }
            if (board == null) {
                board = row;
            } else {
                T next = ops.and(board, row);
                ops.drop(board);
                ops.drop(row);
                board = next;
            }
        }
        return board;
    }
}
