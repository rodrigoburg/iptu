#-*- coding: utf-8 -*-
#exigências: 1) ter o PhantomJS instalado e 2) um servidor local do MongoDB rodando

from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
from threading import Thread

#acha o dígito verificador (função adaptada do javascript do site usado para verificar)
def retornaDigito(setor,quadra,lote):
    strVerif = setor + quadra + lote
    ind = 2
    wsoma = 0
    posfinal = len(strVerif) - 1
    for i in reversed(range(posfinal+1)):
        char = int(strVerif[i])
        wsoma = wsoma + (char * ind)
        ind = ind + 1
        if ind ==11:
            ind = 1
    wresto = 11 - (wsoma % 11)
    if wresto == 10:
        dac = "1"
    elif wresto == 11:
        dac = "0"
    else:
        dac = str(wresto); 
    return dac

#função-modelo - serve só para mostrar a lógica por trás 								
def descobreDono(setor,quadra,lote):
    digito = retornaDigito(setor,quadra,lote)
    url = "https://www3.prefeitura.sp.gov.br/sf8663/formsinternet/principal.aspx"
    driver = webdriver.Firefox()
    driver.get(url)
    elem = driver.find_element_by_name("txtSetor")
    elem.send_keys(setor)
    elem = driver.find_element_by_name("txtQuadra")
    elem.send_keys(quadra)
    elem = driver.find_element_by_name("txtLote")
    elem.send_keys(lote)
    elem = driver.find_element_by_name("txtDigito")
    elem.send_keys(digito)
    elem = driver.find_element_by_name("_BtnAvancarDasii")
    elem.click()
    elem = driver.find_element_by_name("txtNome")
    nome = elem.get_attribute("value")
    elem = driver.find_element_by_name("txtEndereco")
    end = elem.get_attribute("value")
    elem = driver.find_element_by_name("txtNumero")
    num = elem.get_attribute("value")
    elem = driver.find_element_by_name("txtComplemento")
    comp = elem.get_attribute("value")
    print(nome + " - " + end + " - " + num + "-" + comp)
    return nome

#função para descobrir se todos os elementos são iguais
def all_same(items):
    return all(x == items[0] for x in items)

def fazConsultas(setor1,setor2,registros_antigos):
    #inicia o banco de dados
    client = MongoClient()
    my_db = client["iptu"]
    my_collection = my_db["registros"]
    
    #inicia o webdriver
    url = "https://www3.prefeitura.sp.gov.br/sf8663/formsinternet/principal.aspx"
    # driver = webdriver.Firefox()
    driver = webdriver.PhantomJS()
    #lista para quebrar o loop do setor se as últimas cinco quadras não tiverem nenhum lote válido
    ultimos_45_lotes = ["continue"]
        
    for s in range(setor1,setor2):
        setor = retornaSetor(s)
        #para cada uma das quadras desse setor
        for q in range(1,900): 
            driver.get(url)
            #coloca a quadra no formato '001'
            quadra = '%03d' % q 
            ultimos_cinco_lotes = []
            
            #sai desse setor se as últimas cinco quadras só tiverem dado 'Não localizado'
            if all_same(ultimos_45_lotes):
                if ultimos_45_lotes[0] == "Não localizado":
                    break
    
            #para cada lote dentro dessa quadra
            for i in range(1,9000): 
                registro = {}
                #coloca o lote no formato '0001'
                lote = '%04d' % i

                #checa se o registro já está na base
                if(setor + "-" + quadra + "-" + lote) in registros_antigos:
                    print(setor + "-" + quadra + "-" + lote +": Já existente")
                else:
            
                    #acha o dígito verificador
                    digito = retornaDigito(setor,quadra,lote)
                
                    #manda as inftos
                    elem = driver.find_element_by_name("txtSetor")
                    elem.send_keys(setor)
                    elem = driver.find_element_by_name("txtQuadra")
                    elem.send_keys(quadra)
                    elem = driver.find_element_by_name("txtLote")
                    elem.clear()
                    elem.send_keys(lote)
                    elem = driver.find_element_by_name("txtDigito")
                    elem.clear()
                    elem.send_keys(digito)
            
                    #try para pegar a exceção que representa um lote cancelado
                    try:
                        #avança para a próxima página
                        elem = driver.find_element_by_name("_BtnAvancarDasii")
                        elem.click()
                        #pega os valores da página
                        elem = driver.find_element_by_name("txtNome")
                        registro['nome'] = elem.get_attribute("value")
                
                        #testa se os últimos cinco valores foram não localizados, para trocar de lote
                        ultimos_cinco_lotes.append(registro['nome'])
                        #deixa os últimos 45 lotes só com esse tamanho, para quebrar o loop de quadra 
                        #se todas tiverem sido canceladas (Não Localizado)
                        ultimos_45_lotes.append(registro['nome'])
                        if len(ultimos_45_lotes) > 45:
                            ultimos_45_lotes = ultimos_45_lotes[0:44]
                        
                        if len(ultimos_cinco_lotes)> 6:
                            ultimos_cinco_lotes.pop(0)
                            #só quebra o loop se já estivermos após os 15 primeiros lotes
                            #isso é necessário pois há várias quadras com os primeiros lotes cancelados
                            if i > 15:
                                #se o dono dos últimos cinco lotes forem o mesmo
                                if all_same(ultimos_cinco_lotes):
                                    #e se esse dono for "Não Localizado", quebre o loop
                                    if ultimos_cinco_lotes[0] == "Não localizado":
                                        break
                
                        #pega as outros infos além do nome
                        elem = driver.find_element_by_name("txtEndereco")
                        registro["endereco"] = elem.get_attribute("value")
                        elem = driver.find_element_by_name("txtNumero")
                        registro["numero"] = elem.get_attribute("value")
                        elem = driver.find_element_by_name("txtComplemento")
                        registro["complemento"] = elem.get_attribute("value")
                
                        #acrescenta os dados relativos ao codigo
                        registro["codigo"] = setor + "-" + quadra + "-" + lote
                
                        #se houver nome para o imóvel, insere no banco de dados
                        if registro["nome"] != "Não localizado":
                            my_collection.insert(registro)
                        print(setor + "-" + quadra + "-" + lote + ": "+ registro["nome"] + " - " + registro["endereco"] + " - " + registro["numero"] + " - " + registro["complemento"])
                
                        #volta à página anterior e coloca outro lote para pesquisar
                        driver.back()
                        time.sleep(1)

                    #ignora se o registro houver sido cancelado
                    except NoSuchElementException:
                        pass
            
    
    driver.close()

def registrosAntigos():
    client = MongoClient()
    my_db = client["iptu"]
    my_collection = my_db["registros"]
    registros = []
    for r in my_collection.find():
        registros.append(r['codigo'])
    return registros

def retornaSetor(i):
    return '%03d' % i


def comecaThread(x,y,threads):
    antigos = registrosAntigos()
    thread = Thread(target = fazConsultas, args = (x,y,antigos, ))
    thread.start()
    threads.append(thread)
    return threads
        
threads = []
threads.append(comecaThread(11,30,threads))
threads.append(comecaThread(32,60,threads))
threads.append(comecaThread(62,90,threads))

for t in threads:
    t.join()
#fazConsultas()
#veRegistros()