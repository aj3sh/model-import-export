model-import-export
===================
Imports and Exports django model to excel and csv


Requirement
-----------
	python >= 3
	Django 1.11.5, >= 2.11

Installation
------------
	pip install model-import-export

Usage
-----

**Creating resources**

In your `example_app/resources.py`

```python
from model_import_export.resources import ModelResource, ForeignKeyResource, ManyToManyResource

from dashboard.models import *

class UserResource(ModelResource):
	
	class Meta:
		model = User
		fields = '__all__'
```

**Exporting model**

```python
from .resources import UserResource

queryset = User.objects.all()
resource = UserResource(queryset)
resource.to_excel('users.xlsx')
```

**Importing model**

```python
resource = UserResource()
resource.from_excel('users.xlsx')
```

## Model Import/Export Example
![GitHub model_import_export_example](https://github.com/aj3sh/model_import_export_example)

