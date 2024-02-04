# optimalportfolio
python 

1. read stock close price from data source
2. generate risk and return data 
3. do the analysis to find out the tangent portfolio
4. excel read csv file input and your own position for portfolio management

![alt text](doc/piechart.png?raw=true "GenPortfolio3.py")
![alt text](doc/correlation.png?raw=true "Correlation.py")
![alt text](doc/yield_curve.png?raw=true "GenYieldCurve.py")



# virtual environment setup
1. pip install virtualenv
2. py -m venv myenv  #venv for python3 , env folder name: myenv
3. cd myenv/script
4. .\pip.exe install -r ..\..\requirements.txt  #using pip in myenv/script , here is window example
5. .\pip.exe list
6. configure intellij to myenv 
      refer to https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html#python_create_virtual_env
     
7. .\python.exe ..\..\scripts\genportfolio3.py
      

