#-*- coding: utf-8 -*-
#exigências: 1) ter o PhantomJS instalado e 2) um servidor local do MongoDB rodando

from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
import threading

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

    def raspa_dados_e_salva(self):
        self.raspa_dados_da_pagina()
        self.salva_na_base()
        print "---------------------------------------------------------------------------------------------"
        print "Setor: " + self.setor + " | Quadra: " + self.quadra  + " | Lote: " + self.lote + " | Nome: " + self.nome


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
            except NoSuchElementException:
                controle01 = False
                pass
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
        if existe_na_base(self):
            my_collection.update({'id': self.id},self._formata_para_base())
            #Atualiza o lote da base com os dados atuais
        else:
            my_collection.insert(self._formata_para_base())
            #Salva o lote atual como um novo lote

    def existe_na_base(self):
        """Verifica se o lote já está na collection
            Retorno: retorna True se o lote está na base e False caso não esteja"""
        #Faz a consulta
        my_document = self.consulta_na_base()
        if my_document:
            return True
        else:
            return False

    def consulta_na_base(self):
        """Consulta se o lote existe na base.
            Caso exista, retorna o lote.
            Caso não exista, retorna None"""
        client = MongoClient()
        my_db = client[self.DBASE['dbname']]
        my_collection = my_db[self.DBASE['main_collection']]
        my_document = my_collection.find_one({'id': self.id})
        return my_document

    def carrega_da_base(self):
        """Recupera o lote atual da base de dados carrega os valores nas
            variáveis do objeto atual, caso o lote exista na base."""
        my_document = self.consulta_na_base()
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

def adiciona_nova_thread(result_queue, setor, quadra, num_lote):
    """Função que adiciona uma nova thread na lista de threads, consultando mais um lote"""
    lote = Lote(setor, quadra, num_lote)
    if not lote.existe_na_base():
        result_queue.put(lote.raspa_dados_e_salva())

threads = []

total_threads_simultaneas = 20
total_setores = 999
total_quadras = 999
total_lotes = 9999
n = 0

feitos = {}

for setor in range(1,total_setores+1):
    feitos[setor] = {}
    for quadra in range(1, total_quadras+1):
        feitos[setor][quadra] = []
        for num_lote in range(1,total_lotes+1):
            feitos[setor][quadra].append(lote)
            t = threading.Thread(target=carrega_lote, args=[result_queue, setor, quadra, num_lote])
            threads.append(t)
            t.start()
            n = n + 1
            if n = total_threads_simultaneas:
                print "Waiting for some results"
                for t in threads:
                    t.join()
                n = 0
