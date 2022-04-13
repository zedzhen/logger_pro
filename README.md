# logger_pro
Модуль для логирования работы функций, использующий декоратор.

## Ограничения
- Объекты которые вы хотите логировать, не должны содержать атрибут "logger_pro"\
Иначе он будет переопределён/некорректное декорирование методов класса
- Внутри функций не используйте переменную \_\_getstate\_\_, кроме как для этого модуля.

## Уровни логирования
все уровни являются экземплярами класса Logger.LogLevel \
**Всегда** используйте Logger.LEVEL
### ERROR
- Все ошибки наследуемые от Exception
### WARNING
- Все ошибки 
### INFO
- Все ошибки
- Функция запустилась/закончила выполнение
### DEBUG
- Все ошибки
- Функция запустилась/закончила выполнение
- локальные переменные внутри функции на момент выхода
### NOLOG
- ничего не логируется

## Логирование локальных переменных
все уровни являются экземплярами класса Logger.SerializeType \
**Всегда** используйте Logger.TYPE \
Для десериализации можно использовать функции load_pickle и load_dill
### NOBIN
Словарь имя:значение (в виде__repr__)
### PICKLE
Сериализация с помощью pickle \
Если невозможна, используется NOBIN
### DILL
Сериализация с помощью pickle \
Если невозможна, используется сериализация с помощью dill \
Если невозможна, используется NOBIN
### ONLYDILL
Сериализация с помощью dill \
если невозможна, используется NOBIN
### Несериализуемые объекты
Если у вас в классе есть несериализуемые объекты вы можете использовать метод [\_\_getstate\_\_](https://docs.python.org/3/library/pickle.html#object.__getstate__). \
Если у вас есть несериализуемые локальные переменные, в начале инициализируйте переменную \_\_getstate\_\_, как список строк сериализируемых объектов (остальные объекты будут записаны в соответствии с NOBIN.

## Параметры
- level, уровень логирования.
- serialize, способ сохранения локальных переменных.\
По умолчанию DILL
- raise_error, tuple ошибок, которые надо передавать выше \
По умолчанию все ошибки от Exception поглощаются, а от BaseException передаются дальше
- ignore_error, tuple ошибок, которые будут полностью игнорироваться \
По умолчанию StopIteration и StopAsyncIteration
- out_file, строка (путь до файла), или файловый дескриптор, для записи \
По умолчания sy.stderr
- logger_method, нужно ли декорировать методы класса (с такими же параметрами) \
Если True (по умолчанию) декорируются все методы, которые не были декорированы \
Если False то будет декорирована, только инициализация объекта класса
- pickle_protocol, dill_protocol протоколы сериализации \
По умолчанию pickle.DEFAULT_PROTOCOL и dill.DEFAULT_PROTOCOL

## Значения по умолчанию
Вы можете изменить значения по умолчанию, для всех последующих использований \
Logger.default_NAME

## logger_method
При декорировании функций **не** используется. \
Если True, то при создании объекта класса все его вызываемые переменные (которые не начинаются с "\_\_", и не были уже декорированные) декорируются с теми же параметрами.

## Ошибки
При возникновении ошибки во время инициализации, вызывается исключение InitTypeError(TypeError) \
При невозможности записать в лог во время работы, лог записывается в глобальную переменную GlobalBuffer, и в stderr информация о невозможности записать

При ошибке во время десериализация вызывается исключение десериализация SerializeError(RuntimeError)

## Импорт
При импорте
> from logger_pro import * 

Импортируются Logger, InitTypeError, GlobalBuffer, load_pickle и load_dill
