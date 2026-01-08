#include <iostream>
using namespace std;

int main()
{
    int n = 3;
    int m = 3;
    int arr[][3]
        = { { 3, 2, 7 }, { 2, 6, 8 }, { 5, 1, 9 } };
    int sum = 0;

    // Iterating over all 1-D arrays in 2-D array
    for (int i = 0; i < n; i++) {

        // Printing all elements in ith 1-D array
        for (int j = 0; j < m; j++) {

            // Printing jth element of ith row
            sum += arr[i][j];
        }
    }
    cout << sum << endl;
    return 0;
}
// contributed by akashish__