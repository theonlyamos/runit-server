from datetime import datetime
import uuid

from bson.objectid import ObjectId

from ..common.database import Database

class Model():
    '''A model class'''
    TABLE_NAME = ''
    SELECTED_COLUMNS = []
    WHERE_CLAUSE = []
    GROUP_BY = ''
    ORDER_BY = ()
    LIMIT = 0

    def __init__(self, created_at=None, updated_at=None, id=None):
        self.created_at = (datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S") \
            if not created_at else created_at
        self.updated_at = (datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S") \
            if not updated_at else updated_at
        self.id = uuid.uuid4() if not id else str(id)

    def save(self):
        '''
        Instance Method for saving Model instance to database

        @params None
        @return None
        '''

        data = {}
        
        return Database.db.insert(Model.TABLE_NAME, data)
    
    @classmethod
    def update(cls, update: dict, query={}):
        '''
        Class Method for updating model in database

        @param update Content to be update in dictionary format
        @return None
        '''
        if Database.dbms == 'mongodo':
            update['updated_at'] = (datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S")
        return Database.db.update(cls.TABLE_NAME, Model.normalise(query, 'params'), update)
    
    @classmethod
    def remove(cls, query: dict):
        '''
        Class Method for updating model in database

        @param update Content to be update in dictionary format
        @return None
        '''

        return Database.db.remove(cls.TABLE_NAME, Model.normalise(query, 'params'))
    
    @classmethod
    def count(cls)-> int:
        '''
        Class Method for counting Model Projects

        @params None
        @return int Count of Projects
        '''

        return Database.db.count(cls.TABLE_NAME)

    # @classmethod
    # def get(cls, id = None):
    #     '''
    #     Class Method for retrieving function(s) by _id 
    #     or all if _id is None

    #     @param _id ID of the function in database
    #     @return Function instance(s)
    #     '''

    #     if id is None:
    #         return [cls(**Model.normalise(elem)) for elem in Database.db.find(cls.TABLE_NAME)]

    #     model = Database.db.find_one(cls.TABLE_NAME, Model.normalise({'id': id}, 'params'))
    #     print(model)
    #     return cls(**Model.normalise(model)) if model else None
    
    @classmethod
    def sum(cls, column: str)->int:
        '''
        Class method for retrieving sum of\n
        of specified column in table

        @params None
        @return int Sum of column
        '''
        return Database.sum(cls.TABLE_NAME, column)

    @classmethod
    def get(cls, id = None):
        '''
        Class Method for retrieving model \n
        model data from database

        @param _id ID of Model
        @return List[Model] instance(s)
        '''

        if id is not None:
            model = Database.db.find_one(cls.TABLE_NAME, Model.normalise({'id': id}, 'params'))
            return cls(**Model.normalise(model)) if model else None
        
        query = 'SELECT '
        if cls.SELECTED_COLUMNS:
            query += cls.SELECTED_COLUMNS if type(cls.SELECTED_COLUMNS) is str \
                else ', '.join(cls.SELECTED_COLUMNS)
        else:
            query += "*"
        
        query += f" FROM {cls.TABLE_NAME}"

        if len(cls.WHERE_CLAUSE):
            query += " WHERE"
            for clause in cls.WHERE_CLAUSE:
                if type(clause) is str:
                    query += f" ({clause}) AND"
                elif type(clause) is dict:
                    query += ' ('
                    for key, value in clause.items():
                        query += f"{key}='{value}' AND "
                    query = query.rstrip('AND ').strip()
                    query += ') AND'
        
        query = query.rstrip('AND').strip()
        if cls.GROUP_BY:
            query += f" GROUP BY {cls.GROUP_BY}"
        
        if len(cls.ORDER_BY):
            query += f" ORDER BY {cls.ORDER_BY[0]} {cls.ORDER_BY[1]}"
        
        if cls.LIMIT:
            query += f" LIMIT {cls.LIMIT}"
        
        cls.clear()
        
        return Database.query(query)
    
    @classmethod
    def all(cls)->list:
        '''
        Class Method for retrieving all \n
        model data from database

        @param _id ID of the function in database
        @return List[Model] instance(s)
        '''

        return [cls(**Model.normalise(elem)) for elem in Database.db.find(cls.TABLE_NAME, {})]
        
    @classmethod
    def find(cls, params: dict)-> list:
        '''
        Class Method for retrieving models
        by provided parameters

        @param params
        @return List[Model]
        '''

        return [cls(**Model.normalise(elem)) for elem in Database.db.find(cls.TABLE_NAME, Model.normalise(params, 'params'))]
    
    @classmethod
    def query(cls, column: str, search: str):
        '''
        Class Method for retrieving products
        by their names

        @param name
        @return Product Instance
        '''

        sql = f"SELECT * from {cls.TABLE_NAME} WHERE "
        sql += f"{column} LIKE '%{search}%'"
        
        return [cls(**Model.normalise(elem)) for elem in Database.db.query(sql)]
    
    @classmethod
    def clear(cls):
        '''
        Clear all Class settings
        '''
        cls.SELECTED_COLUMNS = []
        cls.WHERE_CLAUSE = []
        cls.GROUP_BY = ''
        cls.ORDER_BY = ()
        cls.LIMIT = 0
    
    @classmethod
    def select(cls, columns: str|list):
        '''
        Class Method for retrieving model \n
        grouped by specified column

        @param column Column Name to group by
        @return Class
        '''

        cls.SELECTED_COLUMNS = columns
        return cls
    
    @classmethod
    def where(cls, clause: str|list):
        '''
        Class Method for retrieving model \n
        grouped by specified column

        @param column Column Name to group by
        @return Class
        '''

        cls.WHERE_CLAUSE.append(clause)
        return cls
    
    @classmethod
    def group_by(cls, column: str):
        '''
        Class Method for retrieving model \n
        grouped by specified column

        @param column Column Name to group by
        @return Class
        '''

        cls.GROUP_BY = column
        return cls
    
    @classmethod
    def order_by(cls, column: str, order: str = 'ASC'):
        '''
        Class Method for retrieving model \n
        ordered by specified column

        @param column Column Name to group by
        @return Class
        '''

        cls.ORDER_BY = (column, order.upper())
        return cls
    
    @classmethod
    def limit(cls, count: int = 0, offset: int = 0):
        '''
        Class Method for retrieving model \n
        ordered by specified column

        @param column Column Name to group by
        @return Class
        '''

        cls.LIMIT = f"{count}"
        if offset:
            cls.LIMIT += f", {offset}"
        return cls
    
    def json(self)-> dict:
        '''
        Instance Method for converting Model Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''

        return {}
    
    @staticmethod
    def normalise(content: dict, optype: str = 'dbresult')-> dict:
        '''
        Static method of normalising database results\n
        Converts _id from mongodb to id

        @param optype str type of operation: dbresult or params
        @param content Dict|List[Dict] Database result
        @return Dict|List[List] of normalized content
        '''
        normalized = {}
        if Database.dbms == 'mongodb':
            if optype == 'dbresult':
                elem = dict(content)
                elem['id'] = str(elem['_id'])
                del elem['_id']
                for key in elem.keys():
                    if key.endswith('_id'):
                        elem[key] = str(elem[key])
                normalized =  elem
                
            else:
                if 'id' in content.keys():
                    content['_id'] = ObjectId(content['id'])
                    del content['id']
                for key in content.keys():
                    if key.endswith('_id'):
                        content[key] = ObjectId(content[key])
                for key, value in content.items():
                    if type(value) == list:
                        content[key] = '::'.join([str(v) for v in value])
                normalized = content
            return normalized
        return content
