from models.accountmanage_model import AccountmanageModel

class AccountmanageController:
    def __init__(self, plugin_name, data_directory):
        self.model = AccountmanageModel(plugin_name, data_directory)
        self.data_directory = data_directory

    def get_accounts(self, *args, **kwargs):
        """获取所有可用账号"""
        try:
            accounts = self.model.get_available_accounts()
            
            return {
                'success': True,
                'data': accounts,
                'data_directory': self.data_directory+"\\Videos"+"\\Download"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'获取账号列表失败：{str(e)}'
            }

   