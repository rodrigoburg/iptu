#-*- coding: utf-8 -*-
#exigências: 1) ter o PhantomJS instalado e 2) um servidor local do MongoDB rodando

from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
from threading import Thread

class Lote:

    TEMPO_DE_CONTROLE = {
            'get_lote': 3,
            'get_dados_lote': 10
        }

    DBASE = {
            'dbname': 'iptu',
            'main_collection': 'registros',
            'canceled_collection': 'cancelados'
            }

    def __init__(self, setor, quadra, lote):
        self.id = self._codigo_lote()
        self.setor = setor
        self.quadra = quadra
        self.lote = lote
        self.nome = None
        self.cpf = None
        self.cnpj = None
        self.pessoa_fisica = True
        self.endereco = None
        self.numero = None
        self.complemento = None
        self.cod_cadastro_iptu = None
        self.digito_verificador = self._digito_verificador()

    def raspa_dados_da_pagina(self):
        """Faz a consulta do lote na página da prefeitura"""
        url = "https://www3.prefeitura.sp.gov.br/sf8663/formsinternet/principal.aspx"
        driver = webdriver.PhantomJS()
        registro = {}
        controle01 = True
        while(controle01):
            try:
                driver.get(url)

                elem = driver.find_element_by_name("txtSetor")
                elem.send_keys(_formataSetor(setor))
                elem = driver.find_element_by_name("txtQuadra")
                elem.send_keys(_formataQuadra(quadra))
                elem = driver.find_element_by_name("txtLote")
                elem.send_keys(_formataLote(lote))
                elem = driver.find_element_by_name("txtDigito")
                elem.send_keys(self.digito_verificador)
                elem = driver.find_element_by_name("_BtnAvancarDasii")

                controle02 = True
                while(controle02):
                    #loop de controle da requisição dos dados
                    try:
                        elem.click()
                        controle02 = False
                    except:
                        time.sleep(self.TEMPO_DE_CONTROLE['get_dados_lote'])
                        pass

                elem = driver.find_element_by_name("txtNome")
                self.nome = elem.get_attribute("value")
                elem = driver.find_element_by_name("txtEndereco")
                self.endereco = elem.get_attribute("value")
                elem = driver.find_element_by_name("txtNumero")
                self.numero = elem.get_attribute("value")
                elem = driver.find_element_by_name("txtComplemento")
                self.complemento = elem.get_attribute("value")
                elem = driver.find_element_by_name("txtNumIPTU")
                self.cod_cadastro_iptu = elem.get_attribute("value")
                elem = driver.find_element_by_id("rb1")
                self.pessoa_fisica = elem.is_selected() #Se g1 estiver selecionado é PF, senão é PJ
                if (self.pessoa_fisica):
                    elem = driver.find_element_by_name("txtCpf")
                    self.cpf = elem.get_attribute("value")
                else:
                    elem = driver.find_element_by_name("txtCnpj")
                    self.cnpj = elem.get_attribute("value")

                controle01 = False
            except:
                time.sleep(self.TEMPO_DE_CONTROLE['get_lote'])
                pass
        driver.close()

    def salva_na_base(self):
        """Salva o lote na base do mongoDB
            O lote será salvo como um dicionário com as seguintes chaves:
                setor
                quadra
                lote
                nome
                cpf
                cnpj
                pessoa_fisica
                endereco
                numero
                complemento
                cod_cadastro_iptu
         """
        client = MongoClient()
        my_db = client[self.DBASE['dbname']]
        my_collection = my_db[self.DBASE['main_collection']]
        if existe_lote_na_base(self):
            my_collection.update({'id': self.id},self._formata_para_base())
            #Atualiza o lote da base com os dados atuais
        else:
            my_collection.insert(self._formata_para_base())
            #Salva o lote atual como um novo lote

    def existe_lote_na_base(self):
        """Verifica se o lote já está na collection
            Retorno: retorna True se o lote está na base e false caso não esteja"""
        #Faz a consulta
        my_document = self.consulta_lote_na_base()
        if my_document:
            return True
        else:
            return False

    def consulta_lote_na_base(self):
        """Consulta se o lote existe na base.
            Caso exista, retorna o lote.
            Caso não exista, retorna None"""
        client = MongoClient()
        my_db = client[self.DBASE['dbname']]
        my_collection = my_db[self.DBASE['main_collection']]
        my_document = my_collection.find_one({'id': self.id})
        return my_document

    def carrega_lote_da_base(self):
        """Recupera o lote atual da base de dados carrega os valores nas
            variáveis do objeto atual, caso o lote exista na base."""
        my_document = self.consulta_lote_na_base()
        if my_document:
            self.setor = my_document.setor
            self.quadra = my_document.quadra
            self.lote = my_document.lote
            self.nome = my_document.nome
            self.cpf = my_document.cpf
            self.cnpj = my_document.cnpj
            self.pessoa_fisica = my_document.pessoa_fisica
            self.endereco = my_document.endereco
            self.numero = my_document.numero
            self.complemento = my_document.complemento
            self.cod_cadastro_iptu = my_document.cod_cadastro_iptu

    def localizado(self):
        """Retorna falso se o lote for 'não localizado'"""
        if self.nome === "Não localizado":
            return False
        return True

    def _codigo_lote(self):
        """Retorna o código 'setor.quadra.lote'"""
        return self.setor + '-' + self.quadra + '-' + self.lote

    def _formata_setor(s):
        """Retorna o setor com três dígitos. p.ex: 000, 001, 040, etc
            Atributo: setor (int)
        """
        return '%03d' % s

    def _formata_quadra(q):
        """Retorna a quadra com três dígitos. p.ex: 000, 001, 040, etc
            Atributo: quadra (int)
        """
        return '%03d' % q

    def _formata_lote(l):
        """Retorna o lote com quatro dígitos. p.ex: 0000, 0001, 0040, etc
            Atributo: lote (int)
        """
        return '%04d' % l

        #acha o dígito verificador (função adaptada do javascript do site usado para verificar)
    def _digito_verificador(self):
        """Retorna o dígito verificador do SQL.
            Cálculo realizado com base numo javascript verificador do próprio site da prefeitura.
            Atributos:
                - setor (int)
                - quadra (int)
                - lote (int)
        """
        strVerif = self.setor + self.quadra + self.lote
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

    def _formata_para_base(self):
        return {'id': self.id,
                'setor': self.setor,
                'quadra': self.quadra,
                'lote': self.lote,
                'nome': self.nome,
                'cpf': self.cpf,
                'cnpj': self.cnpj,
                'pessoa_fisica': self.pessoa_fisica,
                'endereco': self.endereco,
                'numero': self.numero,
                'complemento': self.complemento,
                'cod_cadastro_iptu': self.cod_cadastro_iptu,
                'digito_verificador': self.digito_verificador
                }













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
                    #TODO: função que consulta um SQL específico na base
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

def main():
    """Função Principal"""

if __name__ == "__main__":
    #código que vai ser efetivamente executado

