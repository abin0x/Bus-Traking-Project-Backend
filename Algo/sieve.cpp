#include <iostream>
#include <vector>
using namespace std;
#define fastread() (ios_base::sync_with_stdio(false), cin.tie(NULL))
using ll = long long;

#define PB push_back
using vl = vector<ll>;

const int M = 1e6;
vl primes;
vector<char> isPrime(M, true);

void sieve() {
  isPrime[0] = isPrime[1] = false;

  for (int i = 4; i < M; i += 2)
    isPrime[i] = false;

  for (ll i = 3; i * i < M; i += 2) {
    if (isPrime[i]) {
      for (ll j = i * i; j < M; j += i)
        isPrime[j] = false;
    }
  }

  for (int i = 2; i < M; i++)
    if (isPrime[i])
      primes.PB(i);
}

void solve() {
  ll n;
  cin >> n;
  for (ll p : primes) {
    if (p >= n)
      break;
    cout << p << " ";
  }
  cout << endl;
}

int main() {
  fastread();
  sieve();
  // ll t;
  // cin >> t;
  // while (t--)
  // {
  solve();
  // }
  return 0;
}