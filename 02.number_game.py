import random


def play_number_game():
    answer = random.randint(1, 100)
    attempts = 0

    print("1부터 100 사이의 숫자를 맞혀보세요!")

    while True:
        guess = input("숫자를 입력하세요: ")

        if not guess.isdigit():
            print("1부터 100 사이의 숫자를 입력해주세요.")
            continue

        guess = int(guess)
        attempts += 1

        if guess < answer:
            print("낮습니다.")
        elif guess > answer:
            print("높습니다.")
        else:
            print(f"정답입니다! {attempts}번 만에 맞히셨습니다.")
            if attempts <= 5:
                print("정말 대단해요! 최고의 기록이에요!")
            elif attempts <= 10:
                print("훌륭해요!")
            else:
                print("축하합니다, 정답을 맞히셨어요!")
            break


if __name__ == "__main__":
    play_number_game()
