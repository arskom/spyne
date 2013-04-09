
from spyne.model.complex import TTableModel
from spyne.model.primitive import UnsignedInteger32
from spyne.model.primitive import Unicode

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker

db = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=db)
TableModel = TTableModel(MetaData(bind=db))


class User(TableModel):
    __tablename__ = 'spyne_user'

    # This is only needed for sqlite
    __table_args__ = {"sqlite_autoincrement": True}

    id = UnsignedInteger32(pk=True)
    user_name = Unicode(32, min_len=4, pattern='[a-z0-9.]+')
    full_name = Unicode(64, pattern='\w+( \w+)+')
    email = Unicode(64, pattern=r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4}')
