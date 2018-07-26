from abc import abstractmethod
from functools import wraps

from catcher.utils.misc import try_get_object, merge_two_dicts, fill_template

registered_steps = {}


def register_class(target_class):
    registered_steps[target_class.__name__.lower()] = target_class


class MetaStep(type):
    def __new__(mcs, name, bases, class_dict):
        cls = type.__new__(mcs, name, bases, class_dict)
        if cls.__name__ != 'Step' or cls.__name__ != 'ExternalStep':
            register_class(cls)
        return cls


class Step(object, metaclass=MetaStep):
    """
    Abstract class for all Steps. Operates with common properties, available for all steps.

    :register: register a new variable at the end of this step. *Optional*
    :name: Set name for this step. Is used for passed steps output. *Optional*
    :ignore_errors: Do not stop the test if this step fails. Can be useful with running includes. *Optional*
    :tag: Tag this step to be called via `run` with tag. *Optional*

    :actions: Each step can have one ore multiple actions. In case of one action `actions` list is
    not necessary and you can use short form. Also - in case of several actions each should have its
    own properties like `register`, `tag` etc...

    One action - short form.
    ::
         http:
             post:  # register client and get id
                  url: '{{ user_service_url }}/sign_up'
                  body: {email: '{{ email }}', name: '{{ user }}'}

    Multiple actions.
    ::
        http:
            actions:
              - post:  # register client and get id
                  url: '{{ user_service_url }}/sign_up'
                  body: {email: '{{ email }}', name: 'TestUser'}
              - post:  # fill some personal data
                  url: '{{ user_service_url }}/data'
                  body: {gender: 'M', age: 22, firstName: 'John', lastName: 'Doe'}

    :Examples:

    Register new variable after `echo` step finishes.
    ::
        echo: {from: '{{ RANDOM_STR }}@test.com', register: {user_email: '{{ OUTPUT }}'}}

    Tag both http actions with `sign_up`
    ::
        http:
            actions:
              - post:  # register client and get id
                  url: '{{ user_service_url }}/sign_up'
                  headers: {Content-Type: 'application/json'}
                  body: {email: '{{ email }}', name: 'TestUser'}
                  response_code: 201
                register: {token: '{{ OUTPUT.data.token }}'}
                tag: sign_up
              - post:  # fill some personal data
                  url: '{{ user_service_url }}/data'
                  headers: {Content-Type: 'application/json', Authorization: '{{ token }}'}
                  body: {gender: 'M', age: 22, firstName: 'John', lastName: 'Doe'}
                register: {uuid: '{{ OUTPUT.data.uuid }}'}
                tag: sign_up

    Use custom name for the step
    ::
      http:
         post:  # register client and get id
              url: '{{ user_service_url }}/sign_up'
              headers: {Content-Type: 'application/json'}
              body: {email: '{{ email }}', name: '{{ user }}'}
              response_code: 201
         name: 'Register {{ user }} on remote server'

    Ignore errors and continue to another step
    ::
        http: {get: {url: 'http://test.com', response_code: 200}, ignore_errors: true}
    """

    def __init__(self, body: dict or str, *params, **kwargs) -> None:
        if isinstance(body, str):
            self.register = None
            self.name = None
        else:
            self.register = body.get('register', None)
            self.name = body.get('name', None)

    @abstractmethod
    def action(self, includes: dict, variables: dict) -> dict or tuple:
        pass

    @staticmethod
    def filter_predefined_keys(data: dict):
        [action] = [k for k in data.keys() if k != 'register' and k != 'ignore_errors' and k != 'name' and k != 'tag']
        return action

    @classmethod
    def construct_step(cls, body, *params, **kwargs):
        return cls(body, *params, **kwargs)

    def process_register(self, variables, output: dict or list or str or None = None) -> dict:
        if self.register is not None:
            for key in self.register.keys():
                if output is not None:
                    out = fill_template(self.register[key],
                                        merge_two_dicts(variables, {'OUTPUT': try_get_object(output)}))
                else:
                    out = fill_template(self.register[key], variables)
                variables[key] = out
        return variables


def update_variables(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if isinstance(result, tuple):
            return self.process_register(result[0], result[1])
        else:
            return self.process_register(result)

    return wrapper
