import datetime
import socket
import cv2
import numpy as np
import requests

BLOCK_SIZE = 8192


# this simple http server script is referenced of the internet
# it's not very important so I'm not gonna comment every line of what it does
def serve(host='0.0.0.0', port=3246):
    try:
        # socket listening on specified port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(1)

        print('Echoing from http://{}:{}'.format(host, port))

        while True:
            connection, client_address = sock.accept()

            request = {}
            bytes_left = BLOCK_SIZE
            while bytes_left > 0:
                if bytes_left > BLOCK_SIZE:
                    data = connection.recv(BLOCK_SIZE)
                else:
                    data = connection.recv(max(0, bytes_left))

                if 'header' not in request:
                    request = build_request(data)
                    header_length = len(request['raw']) - len(request['body'])
                    body_length_read = BLOCK_SIZE - header_length
                    if 'content-length' in request['header']:
                        bytes_left = int(request['header']['content-length']) - body_length_read
                    else:
                        bytes_left = 0
                else:
                    request['raw'] += data
                    request['body'] += data.decode('utf-8', 'ignore')
                    bytes_left -= BLOCK_SIZE

            request_time = datetime.datetime.now().ctime()

            print(' - '.join([client_address[0], request_time, request['header']['request-line']]))

            content = 'DEFAULT'

            # get the url as a GET request, unescaped.
            # since this is a test we assume all urls are valid and we don't check them
            if len(request['header']['request-line']) != 0:
                url_to_parse = request['header']['request-line'].split(' ')[1][1:]

                if url_to_parse != 'favicon.ico':

                    resp = requests.get(url_to_parse, stream=True).raw
                    image = np.asarray(bytearray(resp.read()), dtype="uint8")
                    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
                    b, g, r = cv2.split(image)

                    COLOR_REF = {
                        'teal': [0, 128, 128],
                        'red': [255, 0, 0],
                        'black': [0, 0, 0],
                        'navy': [0, 0, 128]
                    }

                    # for images that contains complex patterns I'd rather first compute a histogram of the color distribution
                    # then just compare the most frequent pixel value to the color_reference values we are checking for
                    # this approach is better than computing the average absolute difference between each pixels and the target colors
                    # especially since rgb is a vector3 value, computing the difference in a noisy setting is not robust

                    # however since the test images look clear and uniform enough, therefore for test purpose I will just demonstrate
                    # how to achieve this by computing the average difference via a for loop,
                    # instead of using built-in opencv or numpy functions

                    # diff_dict = {}
                    # here is how it would have worked with a python for loop, which is too slow for big images
                    # for color_key, color_rgb in COLOR_REF.items():
                    #     avg_diff = 0
                    #     R = len(b)
                    #     C = len(b[0])
                    #     for row in range(R):
                    #         blue_chanel_row = b[row]
                    #         green_chanel_row = g[row]
                    #         red_chanel_row = r[row]
                    #         for col in range(C):
                    #             red = red_chanel_row[col]
                    #             green = green_chanel_row[col]
                    #             blue = blue_chanel_row[col]
                    #
                    #             diff = np.subtract(color_rgb, (red, green, blue))
                    #             avg_diff += np.sum(np.abs(diff))
                    #     diff_dict[color_key] = avg_diff / float(R) / float(C)
                    #
                    # print(diff_dict)
                    # print(min(diff_dict.keys(), key=lambda x: diff_dict[x]))

                    b = np.array(b).mean()
                    g = np.array(g).mean()
                    r = np.array(r).mean()
                    print(b, g, r)
                    # instead of slow for loop we use numpy to compute the mean of each color channel and just compare that to the target color
                    # because the for loops inside numpy are written in c, likely vectorized
                    min_key = min(COLOR_REF.keys(), key=lambda x: np.sum(
                        np.abs([COLOR_REF[x][2] - b, COLOR_REF[x][1] - g, COLOR_REF[x][0] - r])))
                    min_val = np.sum(np.abs(np.array([r, g, b]) - COLOR_REF[min_key]))
                    print(min_val)

                    # here is the color threshold, if it's too big then return too far
                    if min_val > 100 * 3:
                        content = 'no match'
                    else:
                        content = min_key

            # return the response
            response = "HTTP/1.1 200 OK\nAccess-Control-Allow-Origin: *\n\n{}".format(content)
            print("-" * 10)
            print(response)
            print("-" * 40)
            connection.sendall(response.encode())
            connection.close()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock.close()


def build_request(first_chunk):
    lines = first_chunk.decode('utf-8', 'ignore').split('\r\n')
    h = {'request-line': lines[0]}
    i = 1
    while i < len(lines[1:]) and lines[i] != '':
        k, v = lines[i].split(': ')
        h.update({k.lower(): v})
        i += 1
    r = {
        "header": h,
        "raw": first_chunk,
        "body": lines[-1]
    }
    return r


# serve(host='0.0.0.0', port=3246)
serve('localhost', port=3246)
