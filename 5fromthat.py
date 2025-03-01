import requests
import sys
import math
from PyQt5.QtCore import Qt
from PyQt5 import uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow
from dotenv import dotenv_values


LAT_STEP = 0.008
LON_STEP = 0.008
API_KEY = dotenv_values(".env")["API_KEY"]
coord_to_geo_x = 0.0000428
coord_to_geo_y = 0.0000428


def load_map(mp):
    map_request = "http://static-maps.yandex.ru/1.x/?&z={z}&l={type}&ll={ll}&lang=en_US".format(ll=mp.ll(),
                                                                                     z=mp.zoom,
                                                                                     type=mp.type)
    if mp.search_result:
        map_request += "&pt={0},{1},pm2rdm".format(mp.point_lon, mp.point_lat)
    response = requests.get(map_request)
    if not response:
        print("Ошибка выполнения запроса:")
        print(map_request)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(1)

    map_file = "map.png"
    try:
        with open(map_file, "wb") as file:
            file.write(response.content)
    except IOError as ex:
        print("Ошибка записи временного файла:", ex)
        sys.exit(2)

    return map_file


def reverse_geocode(ll):
    geocoder_request_template = "http://geocode-maps.yandex.ru/1.x/?apikey=" + API_KEY + "&geocode={ll}&format=json&lang=en_US"
    geocoder_request = geocoder_request_template.format(**locals())
    response = requests.get(geocoder_request)

    if not response:
        raise RuntimeError(
            """Ошибка выполнения запроса:
            {request}
            Http статус: {status} ({reason})""".format(
                request=geocoder_request, status=response.status_code, reason=response.reason))


    json_response = response.json()


    features = json_response["response"]["GeoObjectCollection"]["featureMember"]
    return features[0]["GeoObject"] if features else None


class SearchResult(object):
    def __init__(self, point, address, postal_code=None):
        self.point = point
        self.address = address
        self.postal_code = postal_code


class MapParams(object):
    def __init__(self):
        self.types = ["map", "sat", "skl"]
        self.lon = 23.808347
        self.lat = 61.503606
        self.point_lon = None  # координаты метки
        self.point_lat = None
        self.zoom = 15
        self.type = self.types[0]

        self.search_result = None
        self.use_postal_code = False


    def ll(self):
        return "{0},{1}".format(self.lon, self.lat)


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main2.ui', self)
        self.mp = MapParams()
        self.initUi()

    def initUi(self):
        self.find.clicked.connect(self.point)
        self.emit.clicked.connect(self.delete)
        self.withindex.clicked.connect(self.point)
        self.address.setReadOnly(True)
        self.new_pic()

    def new_pic(self):
        self.pixmap = QPixmap(load_map(self.mp))
        self.label.setPixmap(self.pixmap)

    def delete(self):
        self.line.clear()
        self.mp.search_result = None
        self.address.clear()
        self.new_pic()

    def keyPressEvent(self, event):
        print("nya")
        if event.key() == Qt.Key_Z and self.mp.zoom < 19:
            self.mp.zoom += 1
        elif event.key() == Qt.Key_X and self.mp.zoom > 2:
            self.mp.zoom -= 1
        elif event.key() == Qt.Key_A:
            self.mp.lon -= LON_STEP * math.pow(2, 15 - self.mp.zoom)
        elif event.key() == Qt.Key_D:
            self.mp.lon += LON_STEP * math.pow(2, 15 - self.mp.zoom)
        elif event.key() == Qt.Key_W and self.mp.lat < 85:
            self.mp.lat += LAT_STEP * math.pow(2, 15 - self.mp.zoom)
        elif event.key() == Qt.Key_S and self.mp.lat > -85:
            self.mp.lat -= LAT_STEP * math.pow(2, 15 - self.mp.zoom)
        elif event.key() == Qt.Key_R:
            self.mp.type = self.mp.types[(self.mp.types.index(self.mp.type) + 1) % 3]
        self.new_pic()

    def mousePressEvent(self, event):
        self.line.clearFocus()
        if event.button() == Qt.LeftButton and event.y() < 468:
            x, y = event.x() - 300, event.y() - 243
            self.mp.point_lon = self.mp.lon + coord_to_geo_x * x * math.pow(2, 15 - self.mp.zoom)
            self.mp.point_lat = self.mp.lat - coord_to_geo_y * y * math.pow(2, 14 - self.mp.zoom)
            self.point(f'{self.mp.point_lon} {self.mp.point_lat}')
            self.new_pic()


    def point(self, *args):
        if self.line.text() != '' or type(args[0]) == str or (self.sender().text() == 'With postal code' and \
                self.address.toPlainText() != ''):
            if type(args[0]) is not bool:
                algo = reverse_geocode(args[0])
            elif self.sender().text() == 'With postal code':
                algo = reverse_geocode(f'{self.mp.point_lon} {self.mp.point_lat}')
            else:
                algo = reverse_geocode(self.line.text())
                place = algo["Point"]["pos"].split()
                self.mp.lon = self.mp.point_lon = float(place[0])
                self.mp.lat = self.mp.point_lat = float(place[1])
            address = algo["metaDataProperty"]["GeocoderMetaData"]["Address"]
            self.mp.search_result = True
            if self.withindex.isChecked() and "postal_code" in address.keys():
                self.address.setPlainText(f'{address["formatted"]}, {address["postal_code"]}')
            else:
                self.address.setPlainText(address["formatted"])
            self.new_pic()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    ex.show()
    sys.exit(app.exec())
