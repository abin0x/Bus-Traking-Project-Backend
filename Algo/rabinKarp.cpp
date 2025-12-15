#include <iostream>
#include <string>
using namespace std;
#define fastread() (ios_base::sync_with_stdio(false), cin.tie(NULL))
using ll = long long;

void rabinKarp(string t, string p) {
  int n = t.size(), m = p.size();
  int d = 256, mod = 101;

  int hp = 0, ht = 0, h = 1;

  for (int i = 0; i < m - 1; i++)
    h = (h * d) % mod;

  for (int i = 0; i < m; i++) {
    hp = (d * hp + p[i]) % mod;
    ht = (d * ht + t[i]) % mod;
  }

  for (int i = 0; i <= n - m; i++) {
    if (hp == ht) {
      bool ok = true;
      for (int j = 0; j < m; j++) {
        if (t[i + j] != p[j]) {
          ok = false;
          break;
        }
      }
      if (ok)
        cout << i << " ";
    }

    if (i < n - m) {
      ht = (d * (ht - t[i] * h) + t[i + m]) % mod;
      if (ht < 0)
        ht += mod;
    }
  }
}

void solve() {
  string t, p;
  cin >> t >> p;
  rabinKarp(t, p);
}

int main() {
  fastread();
  // ll t;
  // cin>>t;
  // while(t--){
  solve();
  // }
  return 0;
}