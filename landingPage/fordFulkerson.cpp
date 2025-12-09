#include <climits>
#include <cstring>
#include <iostream>
#include <vector>

using namespace std;
const int MAX = 1000;
int n;
int cap[MAX][MAX], flow[MAX][MAX];
vector<int> adj[MAX];

int dfs(int s, int t, int f, vector<bool> &vis) {
  if (s == t)
    return f;
  vis[s] = true;
  for (int u : adj[s]) {
    if (!vis[u] && cap[s][u] - flow[s][u] > 0) {
      int df = dfs(u, t, min(f, cap[s][u] - flow[s][u]), vis);
      if (df > 0) {
        flow[s][u] += df;
        flow[u][s] -= df;
        return df;
      }
    }
  }
  return 0;
}

int fordFulkerson(int s, int t) {
  memset(flow, 0, sizeof(flow));
  int maxFlow = 0;
  while (true) {
    vector<bool> vis(n, false);
    int f = dfs(s, t, INT_MAX, vis);
    if (f == 0)
      break;
    maxFlow += f;
  }
  return maxFlow;
}

int main() {
  int m;
  cin >> n >> m;
  for (int i = 0; i < m; i++) {
    int u, v, c;
    cin >> u >> v >> c;
    adj[u].push_back(v);
    adj[v].push_back(u);
    cap[u][v] = c;
  }

  int s, t;
  cin >> s >> t;
  cout << "Maximum Flow: " << fordFulkerson(s, t) << endl;
}