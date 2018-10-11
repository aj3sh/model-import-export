import pandas as pd

from django.db.models import Count
from dateutil.parser import parse
from dateutil.tz import gettz
from django.conf import settings

class ModelResource:
	"""
	Model resources:
	Exports queryset of model into excel and csv file
	And import excel or csv file data into model
	"""

	def __init__(self, queryset=None):
		"""
		Initializing model resource
		Input: queryset (not required)
		"""

		self.__list = None
		if queryset != None:
			self.__process_queryset(queryset)
		del queryset


	def __get_fields(self):
		"""
		-- used for IMPORT EXPORT --
		Returns list of fields for resource
		"""

		has_fields = False
		fields = []

		# fields
		if hasattr(self.Meta, 'fields'):
			
			# fields array
			if type(self.Meta.fields) == list:
				fields = self.Meta.fields
				has_fields = True
			
			# all fields
			elif self.Meta.fields == '__all__':
				for model_field in self.Meta.model._meta.fields:
					fields.append(model_field.name)
				for model_field in self.Meta.model._meta.many_to_many:
					fields.append(model_field.name)
				has_fields = True

		# exlude fields
		elif hasattr(self.Meta, 'exclude'):
			if type(self.Meta.exclude) == list:
				
				for model_field in self.Meta.model._meta.fields:
					if not model_field.name in self.Meta.exclude:
						fields.append(model_field.name)
				
				for model_field in self.Meta.model._meta.many_to_many:
					if not model_field.name in self.Meta.exclude:
						fields.append(model_field.name)
				has_fields = True

		if not has_fields:
			raise Exception('fields is required')

		if 'id' not in fields:
			fields.insert(0, 'id')

		for field in fields:
			field_type = self.Meta.model._meta.get_field(field).get_internal_type()

			if field_type == 'OneToOneField':
				if not hasattr(self, field):
					setattr(self, field, OneToOneResource())

			elif field_type == 'ForeignKey':
				if not hasattr(self, field):
					setattr(self, field, ForeignKeyResource())

			elif field_type == 'ManyToManyField':
				if not hasattr(self, field):
					setattr(self, field, ManyToManyResource())

		return fields


	def __get_database_fields(self):
		"""
		-- used for IMPORT EXPORT --
		Returns list of database fields (normal, foreign, related, m2m) for values
		"""
		fields = self.__get_fields() # getting all fields
		db_fields = list()	# database list to be appended
		temp_attr = None

		for field in fields:
			if hasattr(self, field):	# checking if field has attribute (special field)
				temp_attr = getattr(self, field)
				if type(temp_attr) == OneToOneResource:
					db_fields.append([field, 'o2o'])
				elif type(temp_attr) == ForeignKeyResource:
					db_fields.append([field, 'foreign'])
				elif type(temp_attr) == RelatedResource:
					db_fields.append([field, 'related'])
				elif type(temp_attr) == ManyToManyResource:
					db_fields.append([field, 'm2m'])
			else:
				db_fields.append([field, 'normal'])

		return db_fields


	def __process_queryset(self, queryset):
		"""
		-- used for EXPORT --
		Process queryset into dictionary list that is to be saved
		"""
		db_fields = self.__get_database_fields()	# categoried resource fields wrt db
		
		self.__fields_values = list()	# fields values to be converted in list before renaming and converted to dataframe 
		self.__rename_values = dict()	# foreign key to be rename from 'project__column' to 'project'
		annotate_dict = dict()	# queryset annotate fields for m2m and related fields 
		queryset_values = list()	# queryset values names
				
		for db_field in db_fields:

			if db_field[1] == 'normal':
				# normal field (just add to queryset_values and fields_values)
				self.__fields_values.append( db_field[0] )
				queryset_values.append( db_field[0] )

			elif db_field[1] == 'foreign' or db_field[1] == 'o2o':
				# foreignkey field ( add to queryset_values, fields_values and rename_values)
				self.__fields_values.append( db_field[0] + '__' + getattr(self, db_field[0]).column )
				queryset_values.append( db_field[0] )
				self.__rename_values[db_field[0] + '__' + getattr(self, db_field[0]).column ] = db_field[0]
			
			else:
				# m2m and related fields ( add to fields_values, postprocess_fields and annotate_dict to take just count as its column)
				self.__fields_values.append(db_field[0])
				annotate_dict[db_field[0]] = Count(db_field[0])

		# gettings values from queryset		
		self.__list = list(queryset.order_by('id').values(*queryset_values).annotate(**annotate_dict).values(*self.__fields_values))

		# appending one to many fields to list
		o2m_field = self.__get_o2m_field(db_fields, queryset)
		for i in range(0, len(self.__list)):
			for field in o2m_field[self.__list[i]['id']]:
				self.__list[i][field] = o2m_field[self.__list[i]['id']][field]

		del queryset


	def __get_o2m_field(self, db_fields, queryset):
		"""
		-- used for Export --
		returns o2m and related queryset
		"""

		postprocess_fields = [ db_field[0] for db_field in db_fields if db_field[1] == 'related' or db_field[1] == 'm2m' ]
		o2m_field = dict()
		for obj in queryset:
			o2m_field[obj.id] = dict()
			for field in postprocess_fields:
				texts = [ str(getattr(m2m_obj, getattr(self, field).column)) for m2m_obj in getattr(obj, field).all() ]
				o2m_field[obj.id][field] = ",".join(texts)

		return o2m_field


	def __check_queryset(self):
		"""
		-- used for EXPORT --
		Checks if queryset is available or not before exporting
		"""

		if self.__list == None:
			raise Exception('Cannot export without queryset.')


	def __get_dataframe(self):
		"""
		-- used for EXPORT --
		returns dataframe from the list
		"""
		self.__check_queryset()
		df = pd.DataFrame(self.__list, columns=self.__fields_values)
		df=df.rename(columns = self.__rename_values)
		
		# converting datetimes to Local time
		db_fields = self.__get_database_fields()
		normal_fields = [ db_field[0] for db_field in db_fields if db_field[1] == 'normal']
		
		for field in normal_fields:
			field_class = self.Meta.model._meta.get_field(field).get_internal_type()
			if field_class == 'DateTimeField':
				df[field] = pd.to_datetime(df[field], unit='s')
				try:
					setattr(df, field, getattr(df, field).dt.tz_localize('UTC'))
				except:
					pass
				setattr(df, field, getattr(df, field).dt.tz_convert(settings.TIME_ZONE) )
				df[field] = df[field].apply(lambda x: '' if pd.isnull(x) else str(x))
			elif field_class == 'DateField' or field_class == 'TimeField':
				df[field] = df[field].apply(lambda x: '' if pd.isnull(x) else str(x))


		return df


	def to_excel(self, file_name):
		"""
		saves queryset to respective excel file
		"""
		self.__get_dataframe().to_excel(file_name, index=False)

	def to_csv(self, file_name):
		"""
		saves queryset to respective csv file
		"""
		self.__get_dataframe().to_csv(file_name, index=False)


	def __set_dataframe(self, df):
		"""
		-- used for EXPORT --
		returns dataframe from the list
		"""
		self.__list = list(df.T.to_dict().values())


	def __save_list(self, df):
		"""
		saves list of dictionaries to model (if id is empty creates as new object)
		"""
		update_df = df.loc[ pd.notnull(df['id']) ]	# row that contain id
		self.__update_list(update_df)
		new_df = df.loc[ pd.isnull(df['id']) ]	# row that doesn't contain id (considered as new object)
		self.__create_list(new_df)


	def __update_list(self, df):
		"""
		updates update_df list to model
		"""
		db_fields = self.__get_database_fields()
		
		for row in list(df.T.to_dict().values()):
			row_id = 0
			self_kwargs = dict() # dictionary arguments passed to model object { 'field_name': 'Field_value'}
			m2m_fields = list() # m2m list carrying [ ['field_name', 'field_value'], ... ]

			for field in db_fields:
				
				# converting NaN and NaT to None
				if pd.isnull(row[field[0]]):
					row[field[0]] = None
				else:
					# for date and times
					field_class = self.Meta.model._meta.get_field(field[0]).get_internal_type()
					if field_class == 'DateTimeField':
						row[field[0]] = parse(row[field[0]])
					elif field_class == 'DateField':
						row[field[0]] = parse(str(row[field[0]])).date()
					elif field_class == 'TimeField':
						row[field[0]] = parse(str(row[field[0]])).time() 

				if field[1] == 'normal':
					if field[0] == 'id':
						row_id = int(row[field[0]])
						pass
					else:
						self_kwargs[field[0]] = row[field[0]]
						pass

				elif field[1] == 'o2o':
					column_name = getattr(self, field[0]).column 	# one to one column name
					class_name = self.Meta.model._meta.get_field(field[0]).rel.to 	# one to one class name
					o2o_obj = class_name.objects.filter(**{ column_name: row[field[0]] }).first()
					if o2o_obj:
						self_kwargs[field[0]] = o2o_obj
				
				elif field[1] == 'foreign':
					column_name = getattr(self, field[0]).column 	# foreign key column name
					class_name = self.Meta.model._meta.get_field(field[0]).rel.to 	# forieng key class name
					foreign_obj = class_name.objects.filter(**{ column_name: row[field[0]] }).first()
					if foreign_obj:
						self_kwargs[field[0]] = foreign_obj
				
				elif field[1] == 'm2m':
					m2m_fields.append([field[0], row[field[0]]])

			# updating lists
			try:
				self.Meta.model.objects.filter(id=row_id).update(**self_kwargs)
				self.__save_m2m(row_id, m2m_fields)
			except:
				pass

		pass


	def __create_list(self, df):
		"""
		creates new_df list to model
		"""
		db_fields = self.__get_database_fields()
		
		for row in list(df.T.to_dict().values()):
			self_kwargs = dict() # dictionary arguments passed to model object { 'field_name': 'Field_value'}
			m2m_fields = list() # m2m list carrying [ ['field_name', 'field_value'], ... ]

			for field in db_fields:
				
				# converting NaN and NaT to None
				if pd.isnull(row[field[0]]):
					row[field[0]] = None 
				else:
					# for date and times
					field_class = self.Meta.model._meta.get_field(field[0]).get_internal_type()
					if field_class == 'DateTimeField':
						row[field[0]] = parse(row[field[0]])
					elif field_class == 'DateField':
						row[field[0]] = parse(str(row[field[0]])).date()
					elif field_class == 'TimeField':
						row[field[0]] = parse(str(row[field[0]])).time() 

				if field[1] == 'normal':
					if field[0] != 'id':
						self_kwargs[field[0]] = row[field[0]]
						pass
				
				elif field[1] == 'o2o':
					column_name = getattr(self, field[0]).column 	# one to one column name
					class_name = self.Meta.model._meta.get_field(field[0]).rel.to 	# one to one class name
					o2o_obj = class_name.objects.filter(**{ column_name: row[field[0]] }).first()
					if o2o_obj:
						self_kwargs[field[0]] = o2o_obj

				elif field[1] == 'foreign':
					column_name = getattr(self, field[0]).column 	# foreign key column name
					class_name = self.Meta.model._meta.get_field(field[0]).rel.to 	# forieng key class name
					foreign_obj = class_name.objects.filter(**{ column_name: row[field[0]] }).first()
					if foreign_obj:
						self_kwargs[field[0]] = foreign_obj

				elif field[1] == 'm2m':
					m2m_fields.append([field[0], row[field[0]]])

			try:
				row_obj = self.Meta.model.objects.create(**self_kwargs)
				self.__save_m2m(row_obj.id, m2m_fields)
			except:
				pass


	def __save_m2m(self, obj_id, fields):
		"""
		Save many to many relation of respective fields and values
		"""
		obj = self.Meta.model.objects.filter(id=obj_id).first()
		if not obj:
			return

		for field in fields:
			# if many to many field is empty move to next field
			if pd.isnull(field[1]):
				continue
			
			column_name = getattr(self, field[0]).column 	# m2m column name
			class_name = self.Meta.model._meta.get_field(field[0]).rel.to 	# m2m class name
			
			for value in field[1].split(','):
				m2m_obj = class_name.objects.filter(**{ column_name: value.strip() }).first()
				
				# adding m2m object if exists
				if m2m_obj:
					getattr(obj, field[0]).add(m2m_obj)


	def from_csv(self, file_name):
		"""
		loads data from csv and saves to model
		"""
		df = pd.read_csv(file_name, dtype=object)
		self.__save_list(df)
		pass

	def from_excel(self, file_name):
		"""
		loads data from excel and saves to model
		"""
		df = pd.read_excel(file_name, dtype=object)
		self.__save_list(df)
		pass


class OneToOneResource:
	"""
	OneToOne resource
	Used for foriegnkey field in model resource
	"""
	def __init__(self, **kwargs):
		if kwargs.get('column'):
			self.column = kwargs.get('column')
		else:
			self.column = 'id'

class ForeignKeyResource:
	"""
	Foreign key resource
	Used for foriegnkey field in model resource
	"""
	def __init__(self, **kwargs):
		if kwargs.get('column'):
			self.column = kwargs.get('column')
		else:
			self.column = 'id'


class RelatedResource:
	"""
	Related resource for realted names
	One to many relations
	"""
	def __init__(self, **kwargs):
		if kwargs.get('column'):
			self.column = kwargs.get('column')
		else:
			self.column = 'id'


class ManyToManyResource:
	"""
	Many to Many resource
	Used for many to many field in model resource
	"""
	def __init__(self, **kwargs):
		if kwargs.get('column'):
			self.column = kwargs.get('column')
		else:
			self.column = 'id'