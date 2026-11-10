/**************************************************************************
  BDD demonstration of the N-Queen chess problem.
  -----------------------------------------------
  The BDD variables correspond to a NxN chess board like:

     0    N      2N     ..  N*N-N
     1    N+1    2N+1   ..  N*N-N+1
     2    N+2    2N+2   ..  N*N-N+2
     ..   ..     ..     ..  ..
     N-1  2N-1   3N-1   ..  N*N-1

   So for example a 4x4 is:

     0 4  8 12
     1 5  9 13
     2 6 10 14
     3 7 11 15

   One solution is then that 2,4,11,13 should be true, meaning a queen
   should be placed there:

     . X . .
     . . . X
     X . . .
     . . X .

**************************************************************************/
#include <stdlib.h>
#include <iostream>
#include "bdd.h"

#include "../common/row_args.h"
#define ROW_HANDLE bdd
#define ROW_ONE() bddtrue
#define ROW_ZERO() bddfalse
#define ROW_FALSE bddfalse
#define ROW_BRANCH(v, hi, lo) bdd_ite(bdd_ithvar(v), hi, lo)
#define ROW_AND(a, b) ((a) & (b))
#define ROW_OR(a, b) ((a) | (b))
#define ROW_DROP(x) ((void)0)
#include "../common/row_queens.h"


int N;                /* Size of the chess board */
bdd **X;              /* BDD variable array */
bdd queen;            /* N-queen problem express as a BDD */


/* Build the requirements for all other fields than (i,j) assuming
   that (i,j) has a queen */
void build(int i, int j)
{
   bdd a=bddtrue, b=bddtrue, c=bddtrue, d=bddtrue;
   int k,l;

      /* No one in the same column */
   for (l=0 ; l<N ; l++)
      if (l != j)
	 a &= X[i][j] >> !X[i][l];

      /* No one in the same row */
   for (k=0 ; k<N ; k++)
      if (k != i)
	 b &= X[i][j] >> !X[k][j];

      /* No one in the same up-right diagonal */
   for (k=0 ; k<N ; k++)
   {
      int ll = k-i+j;
      if (ll>=0 && ll<N)
	 if (k != i)
	    c &= X[i][j] >> !X[k][ll];
   }

      /* No one in the same down-right diagonal */
   for (k=0 ; k<N ; k++)
   {
      int ll = i+j-k;
      if (ll>=0 && ll<N)
	 if (k != i)
	    d &= X[i][j] >> !X[k][ll];
   }

   queen &= a & b & c & d;
}


int main(int ac, char **av)
{
   ac = row_args(ac, av);
   using namespace std ;
   int n,i,j;

   if (ac != 2)
   {
      fprintf(stderr, "USAGE:  queen N\n");
      return 1;
   }

   N = atoi(av[1]);
   if (N <= 0)
   {
      fprintf(stderr, "USAGE:  queen N\n");
      return 1;
   }

      /* Initialize with 100000 nodes, 10000 cache entries and NxN variables */
   bdd_init(N*N*256, 10000);
   bdd_setvarnum(N*N);

   queen = bddtrue;

      /* Build variable array */
   X = new bdd*[N];
   for (n=0 ; n<N ; n++)
      X[n] = new bdd[N];

   for (i=0 ; i<N ; i++)
      for (j=0 ; j<N ; j++)
	 X[i][j] = bdd_ithvar(i*N+j);

   if (row_mode) queen = row_queens(N, NULL);
    else {
          /* Place a queen in each row */
       for (i=0 ; i<N ; i++)
       {
          bdd e = bddfalse;
          for (j=0 ; j<N ; j++)
         e |= X[i][j];
          queen &= e;
       }

       const bool show_progress = getenv("BUDDY_NQUEENS_PROGRESS") != nullptr;

          /* Build requirements for each variable(field) */
       for (i=0 ; i<N ; i++)
          for (j=0 ; j<N ; j++)
           {
              if (show_progress)
                 cout << "Adding position " << i << "," << j << "\n" << flush;
          build(i,j);
           }
   }
      /* Print the results */
   const double solutions = bdd_satcount(queen);
   cout << "There are " << solutions << " solutions\n";
   cout << "one is:\n";
   bdd solution = bdd_satone(queen);
   cout << bddset << solution << endl;

   bddStat stats;
   bdd_stats(&stats);
   int alive = bdd_nodecount(queen);
   cout << "NQUEENS_METRICS n=" << N
        << " solutions=" << solutions
        << " nodes_created=" << stats.produced
        << " nodes_alive=" << alive << "\n";

   bdd_done();

   for (i=0 ; i<N ; i++)
      delete [] X[i];
   delete [] X;

   return 0;
}
