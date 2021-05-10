# API Datos eléctricos

**Autor:** Javier Orti Priego (javierorp)

Desarrollo de un script para importar datos CSV a una base de datos y de una API REST (hecha con Flask y Flask-RESTPlus) que permita el acceso a dichos datos. La API está segurizada y guarda las peticiones en memoria caché durante 10 min. Se incluyen test que verifican el correcto acceso a la base de datos con los datos importados y del funcionamiento de la API.

   * [Índice](#api-datos-eléctricos)
      * [Requisitos](#requisitos)
      * [Ficheros disponibles](#ficheros-disponibles)
      * [import_CSV_to_mysql.py](#import_csv_to_mysql.py)
      * [api.py](#api.py)
         * [/login](#/login)
         * [/ (Swagger)](#/-(swagger))
         * [/apielec/ping](#/apielec/ping)
         * [/apielec/getData](#/apielec/getdata)
         * [apielec/getDataById](#apielec/getdatabyid)
         * [apielec/getDataByDate](#apielec/getdatabydate)
         * [apielec/getDataByRange](#apielec/getdatabyrange)
      * [test.py](#test.py)
      * [Solución de problemas](#solución-de-problemas)
         * [PyJWT y Werkzeug](#pyjwt-y-werkzeug)

## Requisitos

- MySQL Community Server 8.0.24
- Python 3.9.5
- Paquetes de Python necesarios
  - mysql-connector-python==8.0.24
  - Flask==1.1.2
  - Flask-Caching==1.10.1
  - flask-restplus==0.13.0
  - Werkzeug==0.16.1
  - PyJWT==2.1.0

Para instalar los paquetes puede utilizar el fichero *requirements.txt*:

```powershell
PS > pip install -r requirements.txt
```

o si se quiere instalar en un entorno virtual:

```powershell
PS > pipenv install -r requirements.txt
```

Lo aquí descrito ha sido probado y desarrollado en Windows 10 Home (versión 20H2, compilación 19042.964).

## Ficheros disponibles

- **requirements.txt:** contiene los paquetes de python necesarios para importar los datos y ejecutar la API.
- **Monitoring_report.csv:** contiene los datos a importar a la base de datos y de los que hará uso la API.
- **import_CSV_to_mysql.py:** script para importar los datos del fichero CSV *Monitoring_report.csv* que deberá pasarse como argumento. Crea la base de datos, tablas y usuario necesarios para hacer uso de la API.
- **api.py:** levanta la API para que pueda hacerse uso de ella en el puerto 5.000. Tiene habilitado el modo *debug*.
- **test.py**: contiene 8 test unitarios que comprueban tanto si la base de datos está creada correctamente como si la API responde como debe.

## import_CSV_to_mysql.py

Este script importa los datos de *Monitoring_report.csv*, para lo que crea una base de datos llamada *elecprod* y una tabla *consumpdata*, donde serán volcados los datos. Además, crea un una tabla de usuarios *users*, que serán los usuarios que pueden acceder a la API, un trigger para que todas las contraseñas no se almacenen en texto plano, sino que se almacene el hash SHA1 256 que producen, e inserta en dicha tabla un usuario *rick* con contraseña *morty*. Por último, para acceder a la base de datos y porder hacer consultas, crea un usuario de solo consulta (solo puede realizar *select*) sobre la base de datos *elecprod*, con nombre *blue* y contraseña *blue21*, en la máquina local.

A la base de datos local para llevar a cabo todo lo descrito se accede con usuario *root* y contraseña *admin*, por lo que si difieren se deben cambiar en el script (variables *db_user* y *db_pass*).

Las instrucciones SQL que ejecuta el script son las siguientes:

```sql
-- Creación de la base de datos
CREATE DATABASE IF NOT EXISTS elecprod DEFAULT CHARACTER SET 'utf8';

-- Creación de la tabla
CREATE TABLE IF NOT EXISTS elecprod.consumpdata (
    id INT NOT NULL AUTO_INCREMENT COMMENT 'Row id',
    date DATETIME NOT NULL COMMENT 'Date of consumption',
    energy DECIMAL(15 , 5 ) COMMENT 'Energy (kWh)',
    reactive_energy DECIMAL(15 , 5 ) COMMENT 'Reactive energy (kVArh)',
    power DECIMAL(15 , 5 ) COMMENT 'Power (kW)',
    maximeter DECIMAL(15 , 5 ) COMMENT 'Maximeter (kW)',
    reactive_power DECIMAL(15 , 5 ) COMMENT 'Reactive power (kVAr)',
    voltage DECIMAL(15 , 5 ) COMMENT 'Voltage (V)',
    intensity DECIMAL(15 , 5 ) COMMENT 'Intensity (A)',
    power_factor DECIMAL(15 , 5 ) COMMENT 'Power factor (Fi)',
    PRIMARY KEY (id)
);

-- Creación de la tabla con los usuarios que pueden acceder a la API
CREATE TABLE IF NOT EXISTS elecprod.users (
    id INT NOT NULL AUTO_INCREMENT COMMENT 'Row id',
    user CHAR(10) COMMENT 'Authorized user',
    password CHAR(200) COMMENT 'Password encoded in SHA1 256',
    PRIMARY KEY (id),
    UNIQUE KEY (user)
);

-- Eliminación el trigger si ya existe
DROP TRIGGER IF EXISTS elecprod.encpassword;

-- Creación del trigger que encripta las contraseñas
CREATE 
    TRIGGER  encpassword
 BEFORE INSERT ON elecprod.users FOR EACH ROW 
    SET NEW . password = SHA2(NEW.password, 256);

-- Creación del usuario de acceso a la API
INSERT INTO elecprod.users(user, password)VALUES('rick', 'morty');

-- Creación del usuario de solo consulta a la DB y asignación de permisos
CREATE USER IF NOT EXISTS 'blue'@'localhost' IDENTIFIED BY 'blue21';
GRANT SELECT, SHOW VIEW ON elecprod.* TO 'blue'@'localhost';
```

Como se puede ver en el código de creación de la tabla *consumpdata*, se incluye un id auto incremental que actúa como clave primaria, al igual que en la tabla *users*, donde, además del id que es clave primaria, se incluye el campo *user* como clave única, de forma que no pueda haber dos usuarios con el mismo nombre.

Ejecución del script:

```powershell
PS > python import_CSV_to_mysql.py Monitoring_report.csv
OK - Database connection
OK - 'elecprod' database
OK - 'elecprod.consumpdata' table
OK - 'elecprod.users' table
OK - Trigger
OK - User
OK - Database connection
OK - 'blue' user
OK - CSV (11716 lines) successfully imported to elecprod.consumpdata
```

## api.py

Es una API REST hecha con Flask y Flask-RESTPlus, está segurizada y tiene un caché de 10 minutos. La elección de hacer una API REST es por la facilidad de uso ya que, independientemente del lenguaje de programación que se utilice, se puede acceder a ella al solo hacer falta peticiones POST y GET.

Flask es un framework minimalista de Python para crear aplicaciones webs muy sencillo de implementar, que consume pocos recursos y de uso libre. Flask-RESTPlus es una extensión de Flask para construir APIs y que permite implementar Swagger. La función principal de esta API es el acceso a la información contenida en la tabla *consumpdata* de la base de datos *elecprod*.

Para ejecutar la api:

```powershell
PS> python api.py
2021-05-09 15:09:37.150 INFO api - check_database: Database connection OK
 * Serving Flask app "api" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
2021-05-09 15:09:37.165 INFO _internal - _log:  * Restarting with stat
2021-05-09 15:09:37.759 INFO api - check_database: Database connection OK
2021-05-09 15:09:37.775 WARNING _internal - _log:  * Debugger is active!
2021-05-09 15:09:37.775 INFO _internal - _log:  * Debugger PIN: 180-314-403
2021-05-09 15:09:37.790 INFO _internal - _log:  * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

```

La API, como se ve en la última línea, se encuentra corriendo en nuestra máquina (127.0.0.1) en el puerto 5.000. Antes de estar disponible, se comprueba que puede acceder a la base de datos y obtiene de ella las columnas de la tabla *consumpdata*, que serán utilizadas en la respuesta a las peticiones.

Las direcciones disponibles son las siguientes:

```json
/
|-login
|-apielec
	|-ping
	|-getData
	|-getDataById
	|-getDataByDate
	|-getDataByRange
```

Excepto "login", todas las funcionales cuelgan de "apielec". Del mismo modo, todas permiten peticiones GET excepto "login" (aunque lo permite de prueba).

### /login

Para poder acceder a la API es necesario obtener un token que se usará como API Key. Para ello, debemos hacer una petición POST a la dirección http://127.0.0.1:5000/login con autorización de tipo "Basic Auth", usuario "rick" y contraseña "morty".

Aunque en un entorno real las peticiones se realizarían directamente desde otra aplicación, para probarla desde el navegador, si no se quiere utilizar aplicaciones para realizar peticiones como Postman, se ha permitido las peticiones GET, lo que implica que en el navegador se abrirá una ventana emergente solicitando el usuario y contraseña.

Si la petición es inválida devolverá:

```json
{
  "message": "Invalid user and/or password", 
  "status": "ERROR", 
  "statusCode": "401"
}
```

Y si es correcta:

```json
{
  "Authorization_type": "API Key", 
  "In": "header", 
  "Key": "SESSION", 
  "value_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoicmljayJ9.jVk2x58TIaYxetUSLO_wfFk4BkI9saTtCPU8KD8DaQM"
}
```

El token obtenido será el que deba utilizarse para las peticiones a la API, donde **las autorizaciones deberán ser de tipo "API KEY", con clave (*key*) "SESSION", valor (*value*) el token obtenido y añadidas a la cabecera (*header*) de la petición**. Una vez se accede a la API con el token obtenido, esta la guarda indefinidamente en memoria hasta que la API sea reiniciada.

### / (Swagger)

En el directorio principal de la API podemos ver la documentación. Así, accediendo a la dirección http://127.0.0.1:5000/ desde nuestro navegador se muestran todas peticiones accesibles de la API, con una pequeña descripción de cada una de ellas, los parámetros que aceptan y las respuestas que devuelven.

Como la API está segurizada, aunque se pueda ver la documentación, no se pueden realizar peticiones. Para permitir hacer peticiones, debemos pulsar en "Authorize" (arriba a la derecha) e introducir nuestro token. Con ello, ya podríamos lazar peticiones directamente desde Swagger.

Si realizamos peticiones sin autenticarnos obtendremos:

```json
{
  "status": "Token is missing",
  "statusCode": "405"
}
```

Si, por el contrario, el token es erróneo obtendremos:

```json
{
  "status": "Token is invalid",
  "statusCode": "406"
}
```

### /apielec/ping

Solo sirve para comprobar que la API está accesible y ejecutándose correctamente. Haciendo una petición GET a la dirección http://127.0.0.1:5000/apielec/ping correctamente autenticado, se obtiene la siguiente respuesta:

```json
{
    "message": "I'm here!!",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 0,
        "records": []
    }
}
```

### /apielec/getData

| Parámetros | Tipo | Descripción |
| ---------- | ---- | ----------- |
| -          | -    | -           |

| Respuesta (código) | Descripción                            |
| ------------------ | -------------------------------------- |
| 200                | OK                                     |
| 405                | Token is missing (token no encontrado) |
| 406                | Invalid token (token no válido)        |

Obtiene todos los datos que se encuentran disponibles en la base de datos. Por lo que al realizar una petición GET a la dirección http://127.0.0.1:5000/apielec/getData correctamente autenticado, la consulta que realiza a base de datos es la siguiente:

```sql
SELECT * FROM elecprod.consumpdata;
```

obteniendo la respuesta:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 11716,
        "records": [
            {
                "date": "2019-08-01 00:00:00",
                "energy": "1.21100",
                "id": "1",
                "intensity": "53.00300",
                "maximeter": "5.30600",
                "power": "5.15600",
                "power_factor": "0.85700",
                "reactive_energy": "0.20000",
                "reactive_power": "-8.38200",
                "voltage": "121.95500"
            },
            {
                "date": "2019-08-01 00:15:00",
                "energy": "1.29900",
                "id": "2",
                "intensity": "57.35200",
                "maximeter": "6.21500",
                "power": "5.29700",
                "power_factor": "0.04700",
                "reactive_energy": "0.30000",
                "reactive_power": "-8.29500",
                "voltage": "121.13500"
            },
            ...           
        ]
    }
}
```

### apielec/getDataById

| Parámetros | Tipo   | Descripción                                                  |
| ---------- | ------ | ------------------------------------------------------------ |
| id         | string | Especifica el Id asociado con el registro. Acepta varios identificadores separados por comas (ej: 1,2,3). |

| Respuesta (código) | Descripción                                      |
| ------------------ | ------------------------------------------------ |
| 200                | OK                                               |
| 400                | Invalid argument (argumento no válido)           |
| 405                | Token is missing (token no encontrado)           |
| 406                | Invalid token (token no válido)                  |
| 500                | Mapping Key Error (error de clave de asignación) |

Obtiene todos los registros cuyo identificador o identificadores (separados por comas, ej: 1,2,3) encuentre en la tabla de referencia. Acepta que el parámetro vaya tanto en la cabecera de la petición como en el cuerpo en formato json. Al realizar una petición GET a la dirección http://127.0.0.1:5000/apielec/getDataById correctamente autenticado, la consulta que realiza a base de datos es la siguiente:

```sql
SELECT * FROM elecprod.consumpdata where id in ({id});
```

Por ejemplo, para la petición http://127.0.0.1:5000/apielec/getDataById?id=5,100, obtenemos:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 2,
        "records": [
            {
                "date": "2019-08-01 01:00:00",
                "energy": "1.71000",
                "id": "5",
                "intensity": "78.31200",
                "maximeter": "14.64400",
                "power": "9.42300",
                "power_factor": "0.86900",
                "reactive_energy": "0.61000",
                "reactive_power": "-10.10200",
                "voltage": "122.01000"
            },
            {
                "date": "2019-08-02 00:45:00",
                "energy": "3.20100",
                "id": "100",
                "intensity": "93.34600",
                "maximeter": "14.15700",
                "power": "11.44800",
                "power_factor": "0.07300",
                "reactive_energy": "0.20000",
                "reactive_power": "-13.40000",
                "voltage": "121.33500"
            }
        ]
    }
}
```

### /apielec/getDataByDate

| Parámetros | Tipo   | Descripción                                                  |
| ---------- | ------ | ------------------------------------------------------------ |
| date       | string | Se buscará la fecha y la hora en el formato "AAAA-MM-DD HH: MM: SS". Acepta el signo "%" y el signo "_". |

| Respuesta (código) | Descripción                                      |
| ------------------ | ------------------------------------------------ |
| 200                | OK                                               |
| 400                | Invalid argument (argumento no válido)           |
| 405                | Token is missing (token no encontrado)           |
| 406                | Invalid token (token no válido)                  |
| 500                | Mapping Key Error (error de clave de asignación) |

Obtiene todos los registros cuyo fecha coincida con la solicitada que encuentre en la tabla de referencia. Acepta que el parámetro vaya tanto en la cabecera de la petición como en el cuerpo en formato json. Al realizar una petición GET a la dirección http://127.0.0.1:5000/apielec/getDataByDate correctamente autenticado, la consulta que realiza a base de datos es la siguiente:

```sql
SELECT * FROM elecprod.consumpdata where date like '{date}');
```

Por ejemplo, para la petición http://127.0.0.1:5000/apielec/getDataById?id=5,100, obtenemos:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 10,
        "records": [
            {
                "date": "2019-09-11 00:00:00",
                "energy": "5.80000",
                "id": "3937",
                "intensity": "129.17500",
                "maximeter": "23.35100",
                "power": "23.21600",
                "power_factor": "0.87300",
                "reactive_energy": "0.00000",
                "reactive_power": "-16.68200",
                "voltage": "185.96900"
            },
            {
                "date": "2019-09-11 01:00:00",
                "energy": "4.50000",
                "id": "3941",
                "intensity": "89.68300",
                "maximeter": "20.32200",
                "power": "17.23900",
                "power_factor": "0.89800",
                "reactive_energy": "0.20000",
                "reactive_power": "-7.56100",
                "voltage": "186.71100"
            },
            ...
        ]
    }
}
```

### /apielec/getDataByRange

| Parámetros | Tipo   | Descripción                                                  |
| ---------- | ------ | ------------------------------------------------------------ |
| date       | string | Fecha y hora iniciales en el formato 'YYYY-MM-DD HH:MM:SS' a buscar. Acepta el signo '%' y el signo '_'. |
| end_date   | string | Fecha y hora finales en el formato 'YYYY-MM-DD HH:MM:SS' a buscar. Acepta el signo '%' y el signo '_'. |

| Respuesta (código) | Descripción                                      |
| ------------------ | ------------------------------------------------ |
| 200                | OK                                               |
| 400                | Invalid argument (argumento no válido)           |
| 405                | Token is missing (token no encontrado)           |
| 406                | Invalid token (token no válido)                  |
| 500                | Mapping Key Error (error de clave de asignación) |

Obtiene todos los registros cuyo fecha coincida entre las dos fechas indicadas en la solicitud que encuentre en la tabla de referencia. Acepta que el parámetro vaya tanto en la cabecera de la petición como en el cuerpo en formato json. Al realizar una petición GET a la dirección http://127.0.0.1:5000/apielec/getDataByRange correctamente autenticado, la consulta que realiza a base de datos es la siguiente:

```sql
SELECT * FROM elecprod.consumpdata where date between '{date}' and '{end_date}');
```

Por ejemplo, para la petición http://127.0.0.1:5000/apielec/getDataByRange?date=2019-09-12_10:00:00&end_date=2019-09-12_10:30:00, obtenemos:

```json
{
    "message": "",
    "status": "OK",
    "statusCode": 200,
    "values": {
        "numrecs": 3,
        "records": [
            {
                "date": "2019-09-12 10:00:00",
                "energy": "0.89900",
                "id": "4073",
                "intensity": "18.77900",
                "maximeter": "4.12500",
                "power": "3.53700",
                "power_factor": "0.95700",
                "reactive_energy": "0.60000",
                "reactive_power": "2.39500",
                "voltage": "184.09600"
            },
            {
                "date": "2019-09-12 10:15:00",
                "energy": "1.30100",
                "id": "4074",
                "intensity": "37.31300",
                "maximeter": "11.75800",
                "power": "6.65800",
                "power_factor": "0.95200",
                "reactive_energy": "1.00000",
                "reactive_power": "5.20600",
                "voltage": "183.93800"
            },
            {
                "date": "2019-09-12 10:30:00",
                "energy": "2.69900",
                "id": "4075",
                "intensity": "64.51200",
                "maximeter": "11.58000",
                "power": "10.53400",
                "power_factor": "0.95200",
                "reactive_energy": "1.09900",
                "reactive_power": "-1.08700",
                "voltage": "183.78300"
            }
        ]
    }
}
```

## test.py

Este script contiene 8 test unitarios que comprueban en orden que:

1. Se puede acceder correctamente a la base de datos con el usuario de solo consultas.
2. El usuario de solo consultas no puede insertar datos.
3. La API devuelve un error al intentar acceder con credenciales incorrectas.
4. Con las credenciales correctas la API devuelve un token válido.
5. Se reciben datos correctos al llamar a /apielec/getData
6. Se reciben datos correctos al llamar a /apielec/geById
7. Se reciben datos correctos al llamar a /apielec/getDataByDate
8. Se reciben datos correctos al llamar a /apielec/getDataByRange

Para ejecutar el test:

```powershell
PS > python test.py
........
----------------------------------------------------------------------
Ran 8 tests in 0.246s

OK
```

## Solución de problemas

### PyJWT y Werkzeug

Si la API no permite generar tokens de forma correcta o le es imposible generarlo puede deberse a que la versión del paquete Werkzeug sea incompatible con la versión de PyJWT instalada. Para solucionarlo hay que intalar las versiones que se nombran en los requisitos, es decir, la 0.16.1 para Werkzeug y la 2.1.0 para PyJWT.

```powershell
PS > pip unistall werkzeug
PS > pip install werkzeug==0.16.1

PS > pip unistall pyjwt
PS > pip install pyjwr==2.1.0
```

