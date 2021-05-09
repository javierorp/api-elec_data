import unittest
import mysql.connector
from urllib import request, error, parse
from json import loads, dumps
import base64

class TestDb(unittest.TestCase):
    """Database tests"""

    def test_db_access(self):
        """Test database accesss with only-read user."""

        conn = mysql.connector.connect(host="localhost", user="blue", passwd="blue21")
        cursor = conn.cursor()
        cursor.execute("select energy from elecprod.consumpdata where date = '2019-08-01 07:00:00';")
        res = cursor.fetchone()
        self.assertEqual(float(res[0]), 1.099)
        cursor.close()
        conn.close()

    def test_db_insert(self):
        """Test if only-read user can insert data."""
        conn = mysql.connector.connect(host="localhost", user="blue", passwd="blue21")
        cursor = conn.cursor()
        err = False
        try:
            cursor.execute("insert into elecprod.consumpdata(date, energy, reactive_energy, power, maximeter, reactive_power, voltage, intensity, power_factor)"
                " values(STR_TO_DATE('2019-08-01 00:00:00', '%Y-%m-%d %T'), 1.211, 0.200, 5.156, 5.306, -8.382, 121.955, 53.003, 0.857);")
        except mysql.connector.Error:
            err = True
        
        self.assertTrue(err)
        cursor.close()
        conn.close()
    
class TestApi(unittest.TestCase):
    """Api tests"""

    token = None

    def test0_error_login(self):
        """Test access the api with wrong password."""
        
        err = False
        try:
            url = "http://127.0.0.1:5000/login"
            req = request.Request(url)
            credentials = ('%s:%s' % ("rick", "morty2"))
            encoded_credentials = base64.b64encode(credentials.encode('ascii'))
            req.add_header('Authorization', 'Basic %s' % encoded_credentials.decode("ascii"))
            with request.urlopen(req) as response:
                data = response.read()

        except error.HTTPError:
            err = True
        
        self.assertTrue(err)
    
    def test1_login(self):
        """Test api access with correct credentials."""

        url = "http://127.0.0.1:5000/login"
        enc_data = parse.urlencode([]).encode("ascii") # To make a post call
        req = request.Request(url, data=enc_data)
        credentials = ('%s:%s' % ("rick", "morty"))
        encoded_credentials = base64.b64encode(credentials.encode('ascii'))
        req.add_header('Authorization', 'Basic %s' % encoded_credentials.decode("ascii"))
        data = None
        with request.urlopen(req) as response:
            data = response.read().decode("ascii")

        self.assertIn("Authorization_type", data)
        self.assertIn("SESSION", data)
        self.assertIn("value_token", data)

        data_dict = loads(data)
        token = data_dict["value_token"]
        if len(token) == 0:
            raise AssertionError("Token empty")

        # To use the token for the rest of the tests
        TestApi.token = token

    def test2_getDataById(self):
        """Test getDataById."""

        id = "100"
        url = "http://127.0.0.1:5000/apielec/getDataById?id=" + id
        headers = {
            "User-Agent": "Api_tests",
            "Accept": "application/json",
            "Session": TestApi.token
            }
        req = request.Request(url, headers=headers)

        data = None
        with request.urlopen(req) as response:
            data = response.read().decode("ascii")
        
        data_dict = loads(data)
        self.assertEqual(data_dict["statusCode"], 200)
        self.assertEqual(data_dict["values"]["numrecs"], 1)
        self.assertEqual(data_dict["values"]["records"][0]["id"], id)

    def test3_getData(self):
        """Test getData."""

        url = "http://127.0.0.1:5000/apielec/getData"
        headers = {
            "User-Agent": "Api_tests",
            "Accept": "application/json",
            "Session": TestApi.token
            }
        req = request.Request(url, headers=headers)

        data = None
        with request.urlopen(req) as response:
            data = response.read().decode("ascii")
        
        data_dict = loads(data)
        self.assertEqual(data_dict["statusCode"], 200)
        self.assertEqual(data_dict["values"]["numrecs"], 11716)
        self.assertEqual(data_dict["values"]["records"][0]["id"], "1")

    def test4_getDataByDate(self):
        """Test getDataByDate."""

        date = "2019-09-11 10:45:00"
        url = "http://127.0.0.1:5000/apielec/getDataByDate?date=" + parse.quote_plus(date)
        headers = {
            "User-Agent": "Api_tests",
            "Accept": "application/json",
            "Session": TestApi.token
            }
        req = request.Request(url, headers=headers)

        data = None
        with request.urlopen(req) as response:
            data = response.read().decode("ascii")
        
        data_dict = loads(data)
        self.assertEqual(data_dict["statusCode"], 200)
        self.assertEqual(data_dict["values"]["numrecs"], 1)
        self.assertEqual(data_dict["values"]["records"][0]["date"], date)
        self.assertEqual(data_dict["values"]["records"][0]["id"], "3980")

    def test5_getDataByRange(self):
        """Test getDataByRange."""

        date = "2019-09-11 10:45:00"
        end_date = "2019-09-11 12:%"
        url = "http://127.0.0.1:5000/apielec/getDataByRange?date={0}&end_date={1}".format(parse.quote_plus(date), parse.quote_plus(end_date))
        headers = {
            "User-Agent": "Api_tests",
            "Accept": "application/json",
            "Session": TestApi.token
            }
        req = request.Request(url, headers=headers)

        data = None
        with request.urlopen(req) as response:
            data = response.read().decode("ascii")
        
        data_dict = loads(data)
        self.assertEqual(data_dict["statusCode"], 200)
        self.assertEqual(data_dict["values"]["numrecs"], 6)
        self.assertEqual(data_dict["values"]["records"][0]["date"], date)
        self.assertEqual(data_dict["values"]["records"][2]["id"], "3982")


if __name__ == "__main__":
    unittest.main()