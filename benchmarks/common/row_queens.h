/* Row-by-row N-Queens construction adapted from SSoelvsten/bdd-benchmark,
 * commit 3c521e16ada406d37ae5f960096a567a41df33b9 (MIT).
 * See benchmarks/licenses/bdd-benchmark-MIT.txt.
 * Each operation returns an owned handle; ROW_DROP releases it.
 */
static ROW_HANDLE row_queens(int n, void *context)
{
    ROW_HANDLE board = ROW_ONE();
    for (int i = 0; i < n; ++i) {
        ROW_HANDLE row = ROW_ZERO();
        for (int j = 0; j < n; ++j) {
            ROW_HANDLE placement = ROW_ONE();
            for (int v = n * n - 1; v >= 0; --v) {
                int r = v / n, c = v % n;
                int positive = r == i && c == j;
                int conflict = r == i || c == j || abs(r - i) == abs(c - j);
                if (!positive && !conflict) continue;
                ROW_HANDLE next = positive
                    ? ROW_BRANCH(v, placement, ROW_FALSE)
                    : ROW_BRANCH(v, ROW_FALSE, placement);
                ROW_DROP(placement);
                placement = next;
            }
            ROW_HANDLE next = ROW_OR(row, placement);
            ROW_DROP(row);
            ROW_DROP(placement);
            row = next;
        }
        ROW_HANDLE next = ROW_AND(board, row);
        ROW_DROP(board);
        ROW_DROP(row);
        board = next;
    }
    return board;
}
