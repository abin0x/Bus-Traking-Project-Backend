#include <iostream>
#include <vector>
using namespace std;

int N;
vector<int> pos;
vector<bool> col, diag1, diag2;
long long solutions = 0;

void printBoard() {
  for (int r = 0; r < N; r++) {
    for (int c = 0; c < N; c++)
      cout << (pos[r] == c ? 'Q' : '.');
    cout << endl;
  }
  cout << endl;
}

void backtrack(int r) {
  if (r == N) {
    printBoard();
    solutions++;
    return;
  }
  for (int c = 0; c < N; c++) {
    if (col[c] || diag1[r - c + N - 1] || diag2[r + c])
      continue;
    pos[r] = c;
    col[c] = diag1[r - c + N - 1] = diag2[r + c] = true;
    backtrack(r + 1);
    col[c] = diag1[r - c + N - 1] = diag2[r + c] = false;
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);

  cin >> N;
  pos.assign(N, -1);
  col.assign(N, false);
  diag1.assign(2 * N - 1, false);
  diag2.assign(2 * N - 1, false);
  backtrack(0);
  cout << "Total solutions: " << solutions << endl;
  return 0;
}
gdfgfgdfdsfdfdsfdsdaddassdfdfds