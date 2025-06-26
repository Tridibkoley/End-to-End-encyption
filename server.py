import socket
import threading
import sys
import rsa

# Generate public and private keys
public_key, private_key = rsa.newkeys(1024)
client_public_keys = {}

Host = 'localhost'
Port = 9999  # Choose any free port

clients = []


def listen_for_messages(client, username):
    while True:
        try:
            response = rsa.decrypt(client.recv(1024), private_key).decode('utf-8')
            if response:
                if response == "send_file":
                    file_data = rsa.decrypt(client.recv(1024), private_key).decode('utf-8')
                    with open("new_file", "w") as file:
                        file.write(file_data)
                    print("File received")

                    # Forward file to all other clients
                    with open("new_file", "r") as file:
                        file_contents = file.read(1048576)
                    for user in clients:
                        if user[1] != client:
                            send_file_to_client(user[1], file_contents)
                    continue

                message = f"{username} : {response}"
                send_message_to_all(message, client)
            else:
                print("Message is empty")
        except Exception as e:
            print(f"Error in listen_for_messages: {e}")
            break


def send_message_to_client(client, data):
    try:
        recipient_public_key = client_public_keys[client]
        encrypted = rsa.encrypt(str(data).encode('utf-8'), recipient_public_key)
        client.sendall(encrypted)
    except Exception as e:
        print(f"Error sending message to client: {e}")


def send_message_to_all(data, sender_client):
    for username, client in clients:
        prefix = "[You] : " if client == sender_client else ""
        send_message_to_client(client, prefix + data)


def client_handler(client, username):
    if username:
        clients.append((username, client))
        send_message_to_all(f"{username} has joined the chat", client)
        threading.Thread(target=listen_for_messages, args=(client, username)).start()
    else:
        print("Username is empty")


def send_file_to_client(client, file_contents):
    try:
        pub_key = client_public_keys[client]
        client.sendall(rsa.encrypt("send_file".encode('utf-8'), pub_key))
        client.sendall(rsa.encrypt(str(file_contents).encode('utf-8'), pub_key))
        print("File sent to a client")
    except Exception as e:
        print(f"Error sending file to client: {e}")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((Host, Port))
        print(f"Server started on port {Port}")
    except Exception as e:
        print(f"Bind failed. Error: {e}")
        sys.exit()

    server.listen(5)

    while True:
        client, address = server.accept()
        print(f"Got connection from {address}")

        # Send server public key
        client.sendall(public_key.save_pkcs1(format='PEM'))

        # Receive full public key from client
        client_key_data = client.recv(2048)
        try:
            client_public_key = rsa.PublicKey.load_pkcs1(client_key_data)
        except ValueError:
            print("Failed to load client public key. Skipping client.")
            client.close()
            continue

        # Receive username
        client_username = client.recv(1024).decode('utf-8')
        print(f"Username: {client_username}")

        client_public_keys[client] = client_public_key
        threading.Thread(target=client_handler, args=(client, client_username)).start()


if __name__ == '__main__':
    main()
