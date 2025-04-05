from iaEditais.repositories.database import conn

if __name__ == '__main__':
    conn().select('SELECT True')
