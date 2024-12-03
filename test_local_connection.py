from pymongo import MongoClient

# Replace with your MongoDB connection string
connection_string = "mongodb://localhost:27017"

client = MongoClient(connection_string)
db = client.test  # Use the test database
print(db.list_collection_names())  # Print list of collections in the database
