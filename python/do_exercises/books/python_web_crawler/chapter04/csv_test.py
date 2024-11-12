import csv


class Post:
    def __str__(self):
        return "Post-__str__-function-result"

    def __repr__(self):
        return "Post-__repr__-function-result"


with open("csv_test.csv", "w", encoding="utf-8", newline="") as file:
    writer = csv.writer(file)
    writer.writerows([
        ["id", "name", "age"],
        ["10001", "Bob", 20],
        ["10002", "Jon", 21],
    ])
sql = """\
CREATE TABLE IF NOT EXISTS \
students \
(id VARCHAR(255) NOT NULL, \
name VARCHAR(255) NOT NULL, \
age INT NOT NULL, \
PRIMARY KEY (id))   
"""

print(sql)

print(" a = {}".format("abc\"def\""))
