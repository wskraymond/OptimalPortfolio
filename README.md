# OptimalPortfolio
python 

1. read stock close price from data source
2. generate risk and return data 
3. do the analysis to find out the tangent portfolio
4. excel read csv file input and your own position for portfolio management

![Alt text](./piechart.png?raw=true "GenPortfolio3.py")



# Virtual Environment setup
1. pip install virtualenv
2. py -m venv myenv  #venv for python3 , env folder name: myenv
3. cd myenv\Script
4. .\pip.exe install -r ..\..\requirements.txt  #using pip in myenv/Script , here is window example
5. .\pip.exe list
6. configure intellij to myenv 
      refer to https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html#python_create_virtual_env
     
7. cd ..\..\
8. .\myenv\Scripts\activate.bat  #set Env to virutalenv Path

# Run
python .\scripts\GenPortfolio3.py
      

