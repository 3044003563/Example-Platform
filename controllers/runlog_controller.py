from models.runlog_model import RunlogModel



class RunlogController:
    def __init__(self,plugin_name,data_directory):
        self.plugin_name = plugin_name
        self.data_directory = data_directory
        self.model = RunlogModel(self.plugin_name,self.data_directory)
       
 
    
    def get_log_list(self):
        """获取运行日志列表"""
        try:
            logs = self.model.get_logs()
            return {
                'success': True,
                'data': logs
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }