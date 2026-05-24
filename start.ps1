<#
启动灵犀文件精灵
#>
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "C:\Users\和旭电商\AppData\Roaming\WPS 灵犀\python-env\pythonw.exe" (Join-Path $dir "lingxi_droplet.py")
