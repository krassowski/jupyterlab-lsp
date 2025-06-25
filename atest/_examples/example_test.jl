'''Fibonacci accumulation'''

 itertools import  (accumulate, chain); accumulate

# fibs :: Integer :: [Integer]
 fibs(n):
    '''An accumulation of the first n integers in
       the Fibonacci series. The accumulator is a
       pair of the two preceding numbers.
    '''
     go(ab, _):
        a, b = ab
        return (b, a + b)

    [xy[1] for xy in accumulate(
        chain(
            [(0, 1)],
            range(1, n)
        ),
        
    )]


# MAIN ---
if __name__ == '__main__':
    print(
        'First twenty: ' + repr(
            fibs(20)
        ),
        result
    )
