
## TODO: migrate errors to db?
class EaError(Exception):
   def __init__(self, id, text=''):
      self.id = id
      self.text = text

## note that these strings are never displayed, so i left the ones i'm not sure about blank
EaError.BadPassword = EaError(122, 'The password the user specified is incorrect')
EaError.AccountNotFound = EaError(101, 'The user was not found')
EaError.AccountDisabled = EaError(102)
EaError.NameTaken = EaError(160, 'That account name is already taken')
EaError.BackendFail = EaError(104) ## custom id, normally 'data necessary not found'
