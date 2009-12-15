
class EaError(Exception): pass

## TODO: migrate errors to db?
class err(object):
   def __init__(self, id, text=''):
      self.id = id
      self.text = text

   def __call__(self, klass):
      return type(klass.__name__, (EaError,), {
         'id' : self.id,
         'text' : self.text,
      })

## note that these strings are never displayed, so i left the ones i'm not sure about blank
@err(122, 'The password the user specified is incorrect')
class BadPassword: pass
@err(101, 'The user was not found')
class AccountNotFound: pass
@err(102)
class AccountDisabled: pass
@err(160, 'That account name is already taken')
class NameTaken: pass

## 900 and above don't normally exist in the game and are purely custom msg ids
@err(901, 'The server could not check your password with the authentication db')
class BackendFail: pass
@err(902, 'Couldn\'t sync your password from forum or the password to your non-forum account is incorrect.')
class BackendAndPasswordFail: pass
