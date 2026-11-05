package benchmark;

/** The reuse API defers shared-variable construction until all fields exist. */
final class BackendFields {
    static void generate() {
        org.ants.jndd.diagram.NDD.generateFields();
    }
}
