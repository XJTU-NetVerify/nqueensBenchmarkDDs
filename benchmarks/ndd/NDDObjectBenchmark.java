package benchmark;

import java.util.*;
import jdd.bdd.BDD;

import org.ants.jndd.diagram.NDD;

public class NDDObjectBenchmark {
    public static final int NDD_TABLE_SIZE = 100000000;

    // declare n fields, n bits per field
    private static void declareFields(int n) {
        for (int i = 0;i < n;i++) {
            NDD.declareField(n);
        }
        BackendFields.generate();
    }

    private static void build(int i, int j, int n, NDD[][] impBatch) {
        NDD a, b, c, d;
        a = b = c = d = NDD.getTrue();

        int k, l;

        /* No one in the same column */
        for (l = 0; l < n; l++) {
            if (l != j) {
                NDD mp = NDD.ref(NDD.imp(NDD.getVar(i, j), NDD.getNotVar(i, l)));
                a = NDD.andTo(a, mp);
                NDD.deref(mp);
            }
        }

        /* No one in the same row */
        for (k = 0; k < n; k++) {
            if (k != i) {
                NDD mp = NDD.ref(NDD.imp(NDD.getVar(i, j), NDD.getNotVar(k, j)));
                b = NDD.andTo(b, mp);
                NDD.deref(mp);
            }
        }

        /* No one in the same up-right diagonal */
        for (k = 0; k < n; k++) {
            int ll = k - i + j;
            if (ll >= 0 && ll < n) {
                if (k != i) {
                    NDD mp = NDD.ref(NDD.imp(NDD.getVar(i, j), NDD.getNotVar(k, ll)));
                    c = NDD.andTo(c, mp);
                    NDD.deref(mp);
                }
            }
        }

        /* No one in the same down-right diagonal */
        for (k = 0; k < n; k++) {
            int ll = i + j - k;
            if (ll >= 0 && ll < n) {
                if (k != i) {
                    NDD mp = NDD.ref(NDD.imp(NDD.getVar(i, j), NDD.getNotVar(k, ll)));
                    d = NDD.andTo(d, mp);
                    NDD.deref(mp);
                }
            }
        }

        c = NDD.andTo(c, d);
        b = NDD.andTo(b, c);
        a = NDD.andTo(a, b);
        NDD.deref(d);
        impBatch[i][j] = a;
    }

    public static void solve(int n) {
        long startNanos = System.nanoTime();
        // init NDD library
        NDD.initNDD(NDD_TABLE_SIZE, 1 + Math.max(1000, (int) (Math.pow(4.4, n - 6)) * 1000), 10000);


        // declare ndd fields
        declareFields(n);

        NDD[] orBatch = new NDD[n];
        NDD[][] impBatch = new NDD[n][n];

        for (int i = 0; i < n; i++) {
            NDD condition = NDD.getFalse();
            for (int j = 0; j < n; j++) {
                condition = NDD.orTo(condition, NDD.getVar(i, j));
            }
            orBatch[i] = condition;
        }

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                build(i, j, n, impBatch);
            }
        }

        NDD queen = NDD.getTrue();

        for (int i = 0; i < n; i++) {
            queen = NDD.andTo(queen, orBatch[i]);
            NDD.deref(orBatch[i]);
        }
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                queen = NDD.andTo(queen, impBatch[i][j]);
                NDD.deref(impBatch[i][j]);
            }
        }
        double solutions = NDD.satCount(queen);
        double seconds = (System.nanoTime() - startNanos) / 1_000_000_000.0;
        report(n, queen, solutions, seconds);
    }

    public static void main(String[] args) {
        if (args.length != 1) throw new IllegalArgumentException("Usage: NDDObjectBenchmark <N>");
        solve(Integer.parseInt(args[0]));
    }

    private static void report(int size, NDD root, double solutions, double seconds) {
        Set<NDD> nddNodes = new HashSet<>();
        Set<Integer> bddNodes = new HashSet<>();
        ArrayDeque<NDD> pending = new ArrayDeque<>();
        ArrayDeque<Integer> labels = new ArrayDeque<>();
        pending.push(root);
        while (!pending.isEmpty()) {
            NDD node = pending.pop();
            if (node.isTerminal() || !nddNodes.add(node)) {
                continue;
            }
            for (Map.Entry<NDD, Integer> edge : node.getEdges().entrySet()) {
                pending.push(edge.getKey());
                labels.push(edge.getValue());
            }
        }
        BDD bdd = NDD.getBDDEngine();
        while (!labels.isEmpty()) {
            int label = labels.pop();
            if (label < 2 || !bddNodes.add(label)) {
                continue;
            }
            labels.push(bdd.getLow(label));
            labels.push(bdd.getHigh(label));
        }
        System.out.printf(Locale.ROOT,
            "NQUEENS_METRICS n=%d solutions=%.0f nodes_alive=%d ndd_nodes_alive=%d bdd_nodes_alive=%d seconds=%.6f%n",
            size, solutions, nddNodes.size() + bddNodes.size(), nddNodes.size(), bddNodes.size(), seconds);
    }
}
