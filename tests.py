import requests

AUTH_URL = 'http://127.0.0.1:5001'
HISTORY_URL = 'http://127.0.0.1:5003'

LOGIN_USERNAME = 'brian'
LOGIN_PASSWORD = '12345'

def print_result(label, response):
    print(f'\n--- {label} ---\n')
    print(f'Status Code: {response.status_code}')
    try:
        print(f'Body: {response.json()}')
    except ValueError:
        print(f'Body: {response.text}')

def get_token():
    '''Log in through the Auth service and return an access token'''
    response = requests.post(
        f'{AUTH_URL}/auth/login',
        json={'username': LOGIN_USERNAME, 'password': LOGIN_PASSWORD},
    )
    print_result('Login (Auth service)', response)

    if response.status_code != 200:
        return None
    return response.json()['access_token']

def main():
    token = get_token()
    if not token:
        print('\nCould not log in is Auth service running on port 5001.')
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    # 1. Save a part
    new_part = {
        'part_id': '12345',
        'name': 'Brake Pad Set',
        'price': 49.99,
        'model': 'Tacoma'
    }
    response = requests.post(f'{HISTORY_URL}/history', json=new_part, headers=headers)
    print_result('Save part', response)

    if response.status_code != 201:
        print('\nCould not save the part. Check token and both parts_history_service.py'
              'and the Auth service are running')
        return

    saved_id = response.json()['id']

    # 2 Try saving the same part_id again -> should be 409
    response = requests.post(f'{HISTORY_URL}/history', json=new_part, headers=headers)
    print_result('Save same part again (expect 409)', response)

    # 3 List saved parts
    response = requests.get(f'{HISTORY_URL}/history', headers=headers)
    print_result('List saved parts', response)

    # 4 Remove the part we just saved
    response = requests.delete(f'{HISTORY_URL}/history/{saved_id}', headers=headers)
    print_result('Delete saved part', response)

    # 5 Confirm it's gone
    response = requests.get(f'{HISTORY_URL}/history', headers=headers)
    print_result('List saved parts (after removal)', response)

    # 6 try removing something that no longer exists
    response = requests.delete(f'{HISTORY_URL}/history/{saved_id}', headers=headers)
    print_result('Removed saved part again (expect 404)', response)

    # 7 try without token
    response = requests.get(f'{HISTORY_URL}/history')
    print_result('List saved parts with no token (expect 401)', response)


if __name__ == '__main__':
    main()
