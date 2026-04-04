from devmate.core.config import settings

def main():
    print("Hello from DevMate!")
    print(f"Using Model: {settings.MODEL_NAME}")
    print(f"AI Base URL: {settings.AI_BASE_URL}")


if __name__ == "__main__":
    main()
