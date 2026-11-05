#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include "cudd.h"

static inline size_t idx(size_t n, size_t row, size_t col)
{
    return row * n + col;
}

static DdNode* and_update(DdManager *mgr, DdNode *lhs, DdNode *rhs)
{
    DdNode *tmp = Cudd_bddAnd(mgr, lhs, rhs);
    Cudd_Ref(tmp);
    Cudd_RecursiveDeref(mgr, lhs);
    Cudd_RecursiveDeref(mgr, rhs);
    return tmp;
}

static DdNode* or_update(DdManager *mgr, DdNode *lhs, DdNode *rhs)
{
    DdNode *tmp = Cudd_bddOr(mgr, lhs, rhs);
    Cudd_Ref(tmp);
    Cudd_RecursiveDeref(mgr, lhs);
    Cudd_RecursiveDeref(mgr, rhs);
    return tmp;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <N>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const int N = atoi(argv[1]);
    if (N <= 0) {
        fprintf(stderr, "N must be positive\n");
        return EXIT_FAILURE;
    }

    DdManager *mgr = Cudd_Init(N * N, 0, CUDD_UNIQUE_SLOTS, CUDD_CACHE_SLOTS, 0);
    if (!mgr) {
        fprintf(stderr, "Failed to initialize CUDD manager\n");
        return EXIT_FAILURE;
    }

    const size_t total = (size_t)N * (size_t)N;
    DdNode **board = (DdNode **)malloc(sizeof(DdNode *) * total);
    if (!board) {
        fprintf(stderr, "Out of memory\n");
        Cudd_Quit(mgr);
        return EXIT_FAILURE;
    }

    for (size_t i = 0; i < total; ++i) {
        board[i] = Cudd_bddIthVar(mgr, (int)i);
        Cudd_Ref(board[i]);
    }

    DdNode *queen = Cudd_ReadOne(mgr);
    Cudd_Ref(queen);

    /* Ensure at least one queen per row */
    for (int row = 0; row < N; ++row) {
        DdNode *clause = Cudd_ReadLogicZero(mgr);
        Cudd_Ref(clause);
        for (int col = 0; col < N; ++col) {
            DdNode *var = board[idx(N, row, col)];
            DdNode *tmp = Cudd_bddOr(mgr, clause, var);
            Cudd_Ref(tmp);
            Cudd_RecursiveDeref(mgr, clause);
            clause = tmp;
        }
        DdNode *combined = Cudd_bddAnd(mgr, queen, clause);
        Cudd_Ref(combined);
        Cudd_RecursiveDeref(mgr, queen);
        Cudd_RecursiveDeref(mgr, clause);
        queen = combined;
    }

    /* Build safety constraints for each position */
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            DdNode *a = Cudd_ReadOne(mgr);
            DdNode *b = Cudd_ReadOne(mgr);
            DdNode *c = Cudd_ReadOne(mgr);
            DdNode *d = Cudd_ReadOne(mgr);
            Cudd_Ref(a);
            Cudd_Ref(b);
            Cudd_Ref(c);
            Cudd_Ref(d);

            DdNode *target = board[idx(N, i, j)];

            for (int l = 0; l < N; ++l) {
                if (l == j) continue;
                DdNode *pair = Cudd_bddOr(mgr, Cudd_Not(target), Cudd_Not(board[idx(N, i, l)]));
                Cudd_Ref(pair);
                a = and_update(mgr, a, pair);
            }

            for (int k = 0; k < N; ++k) {
                if (k == i) continue;
                DdNode *pair = Cudd_bddOr(mgr, Cudd_Not(target), Cudd_Not(board[idx(N, k, j)]));
                Cudd_Ref(pair);
                b = and_update(mgr, b, pair);
            }

            for (int k = 0; k < N; ++k) {
                int ll = k - i + j;
                if (ll >= 0 && ll < N && k != i) {
                    DdNode *pair = Cudd_bddOr(mgr, Cudd_Not(target), Cudd_Not(board[idx(N, k, ll)]));
                    Cudd_Ref(pair);
                    c = and_update(mgr, c, pair);
                }
            }

            for (int k = 0; k < N; ++k) {
                int ll = i + j - k;
                if (ll >= 0 && ll < N && k != i) {
                    DdNode *pair = Cudd_bddOr(mgr, Cudd_Not(target), Cudd_Not(board[idx(N, k, ll)]));
                    Cudd_Ref(pair);
                    d = and_update(mgr, d, pair);
                }
            }

            DdNode *cd = Cudd_bddAnd(mgr, c, d);
            Cudd_Ref(cd);
            Cudd_RecursiveDeref(mgr, c);
            Cudd_RecursiveDeref(mgr, d);

            DdNode *bc = Cudd_bddAnd(mgr, b, cd);
            Cudd_Ref(bc);
            Cudd_RecursiveDeref(mgr, b);
            Cudd_RecursiveDeref(mgr, cd);

            DdNode *ab = Cudd_bddAnd(mgr, a, bc);
            Cudd_Ref(ab);
            Cudd_RecursiveDeref(mgr, a);
            Cudd_RecursiveDeref(mgr, bc);

            DdNode *combined = Cudd_bddAnd(mgr, queen, ab);
            Cudd_Ref(combined);
            Cudd_RecursiveDeref(mgr, queen);
            Cudd_RecursiveDeref(mgr, ab);
            queen = combined;
        }
    }

    double solutions = Cudd_CountMinterm(mgr, queen, N * N);
    printf("Solutions: %.0f\n", solutions);

    int nodes_alive = Cudd_DagSize(queen);
    printf("NQUEENS_METRICS n=%d solutions=%.0f nodes_alive=%d\n",
           N, solutions, nodes_alive);

    Cudd_RecursiveDeref(mgr, queen);
    for (size_t i = 0; i < total; ++i) {
        Cudd_RecursiveDeref(mgr, board[i]);
    }
    free(board);
    Cudd_Quit(mgr);

    return EXIT_SUCCESS;
}
