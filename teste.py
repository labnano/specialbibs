def teste(n):
    n_passos = 5
    for i in range(n):
        print(abs( ( (i+n_passos) % (2*n_passos)) - n_passos ))


teste(20)