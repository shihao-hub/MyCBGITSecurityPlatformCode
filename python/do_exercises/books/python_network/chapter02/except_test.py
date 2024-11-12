cnt = 0
while True:
    cnt += 1
    try:
        print(cnt)
        if cnt == 5:
            print(1 + "")
    except Exception as e:
        print(e)
        print("break!")
        break
