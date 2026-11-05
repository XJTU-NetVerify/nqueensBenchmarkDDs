// <copyright file="Program.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace DecisionDiagrams.Bench
{
    using System;
    using DecisionDiagrams;

    /// <summary>
    /// Main program for the benchmarks.
    /// </summary>
    class Program
    {
        /// <summary>
        /// Main entry point.
        /// </summary>
        /// <param name="args">Command line arguments.</param>
        static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Console.Error.WriteLine("Usage: DecisionDiagrams.Bench <board_size> [--use-bdd]");
                Environment.Exit(1);
            }

            int boardSize = int.Parse(args[0]);
            bool useBDD = args.Length > 1 && args[1] == "--use-bdd";

            if (useBDD)
            {
                RunBenchmark<BDDNode>(boardSize, "BDD");
            }
            else
            {
                RunBenchmark<CBDDNode>(boardSize, "CBDD");
            }
        }

        static void RunBenchmark<T>(int boardSize, string nodeType) where T : IDDNode, IEquatable<T>
        {
            var manager = new DDManager<T>();
            var q = new Queens<T>(manager, boardSize);

            q.Run();

            var encoding = q.GetProblemEncoding();
            double solutions = manager.SatCount(encoding);
            int nodesAlive = manager.NodeCount(encoding);

            // Output format expected by benchmark harness
            Console.WriteLine($"NQUEENS_METRICS n={boardSize} solutions={solutions} nodes_alive={nodesAlive}");
        }
    }
}
