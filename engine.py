import requests
from geopy.geocoders import Nominatim
import folium
import webbrowser
import os

class CaronaEngine:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="copiloto_app")
        self.rota_coords = []

    def pegar_coordenadas(self, endereco):
        try:
            local = self.geolocator.geocode(endereco)
            if local:
                return local.longitude, local.latitude
            return None
        except:
            return None

    def calcular(self, origem, destino, paradas_formatadas, cidade, custo_km, tipo_rateio):
        coords_origem = self.pegar_coordenadas(f"{origem}, {cidade}")
        coords_destino = self.pegar_coordenadas(f"{destino}, {cidade}")

        if not coords_origem or not coords_destino:
            return {"texto": "Erro: Não consegui encontrar a Origem ou o Destino no mapa.", "valor_total": 0}

        url_solo = f"http://router.project-osrm.org/route/v1/driving/{coords_origem[0]},{coords_origem[1]};{coords_destino[0]},{coords_destino[1]}?overview=false"
        try:
            res_solo = requests.get(url_solo).json()
            dist_solo = res_solo['routes'][0]['distance'] / 1000
        except:
            return {"texto": "Erro ao calcular a rota solo.", "valor_total": 0}

        pontos_roteiro = [{"nome": "Origem", "coords": coords_origem, "acao": "Embarca"}]
        
        for p in paradas_formatadas:
            coords = self.pegar_coordenadas(f"{p['endereco']}, {cidade}")
            if coords:
                pontos_roteiro.append({"nome": p['nome'], "coords": coords, "acao": p['acao']})
                
        pontos_roteiro.append({"nome": "Destino Final", "coords": coords_destino, "acao": "Desembarca"})


        self.rota_coords = []
        dist_total = 0.0
        passageiros_no_carro = set()
        

        dividas = {p['nome']: 0.0 for p in paradas_formatadas}
        distancia_andada = {p['nome']: 0.0 for p in paradas_formatadas}

        texto_saida = f"🛣️ === RESUMO DO ROTEIRO === 🛣️\n"
        texto_saida += f"Rateio: {tipo_rateio} | Custo: R$ {custo_km:.2f}/km\n\n"


        for i in range(len(pontos_roteiro) - 1):
            p_atual = pontos_roteiro[i]
            p_prox = pontos_roteiro[i+1]


            if p_atual["acao"] == "Embarca" and p_atual["nome"] != "Origem":
                passageiros_no_carro.add(p_atual["nome"])
            elif p_atual["acao"] == "Desembarca" and p_atual["nome"] != "Destino Final":
                if p_atual["nome"] in passageiros_no_carro:
                    passageiros_no_carro.remove(p_atual["nome"])

            url_trecho = f"http://router.project-osrm.org/route/v1/driving/{p_atual['coords'][0]},{p_atual['coords'][1]};{p_prox['coords'][0]},{p_prox['coords'][1]}?geometries=geojson"
            res_trecho = requests.get(url_trecho).json()

            if res_trecho['code'] != 'Ok': continue

            dist_trecho = res_trecho['routes'][0]['distance'] / 1000
            dist_total += dist_trecho
            custo_trecho = dist_trecho * custo_km

            coords_geojson = res_trecho['routes'][0]['geometry']['coordinates']
            self.rota_coords.extend([[lat, lon] for lon, lat in coords_geojson])

            texto_saida += f"➡️ {p_atual['nome']} até {p_prox['nome']} ({dist_trecho:.2f} km)\n"
            texto_saida += f"   Pessoas a bordo: {', '.join(passageiros_no_carro) if passageiros_no_carro else 'Só o Motorista'}\n"


            for nome in passageiros_no_carro:
                distancia_andada[nome] += dist_trecho


            if len(passageiros_no_carro) > 0:
                if tipo_rateio == "Dividir Igual":
                    fatia = custo_trecho / (len(passageiros_no_carro) + 1)
                    for nome in passageiros_no_carro:
                        dividas[nome] += fatia

                elif tipo_rateio == "Cobrar Integral":
                    fatia = custo_trecho / len(passageiros_no_carro)
                    for nome in passageiros_no_carro:
                        dividas[nome] += fatia

        if tipo_rateio == "Divisão Justa (Desvio)":
            desvio = max(0, dist_total - dist_solo)
    
            custo_desvio = desvio * custo_km
            custo_base = dist_solo * custo_km
    

            km_motorista = dist_total
            km_passageiros = {nome: distancia_andada[nome] for nome in distancia_andada}
            total_km_passageiros = sum(km_passageiros.values())

            motorista_paga_base = custo_base / 2

            resto_base = custo_base / 2
        
            for nome in dividas:
                if total_km_passageiros > 0:
                    proporcao = km_passageiros[nome] / total_km_passageiros
                else:
                    proporcao = 0
        
            dividas[nome] = resto_base * proporcao
        
            if total_km_passageiros > 0:
                dividas[nome] += custo_desvio * proporcao
            else:
                dividas[nome] += custo_desvio / len(dividas) if len(dividas) > 0 else 0

        texto_saida += f"\n💰 === FECHAMENTO FINANCEIRO === 💰\n"
        texto_saida += f"Distância Solo Original: {dist_solo:.2f} km\n"
        texto_saida += f"Distância Total Real: {dist_total:.2f} km\n"
        texto_saida += f"Custo Total da Gasolina: R$ {(dist_total * custo_km):.2f}\n\n"

        valor_total_arrecadado = 0
        for nome, valor in dividas.items():
            texto_saida += f"🔹 Passageiro {nome} paga: R$ {valor:.2f}\n"
            valor_total_arrecadado += valor

        return {"texto": texto_saida, "valor_total": valor_total_arrecadado}

    def abrir_mapa(self):
        if self.rota_coords:
            meio = len(self.rota_coords) // 2
            # Mudamos os 'tiles' para o CartoDB para evitar o erro de Access Blocked do OpenStreetMap
            m = folium.Map(location=self.rota_coords[meio], zoom_start=13, tiles='CartoDB positron')
            folium.PolyLine(self.rota_coords, color="blue", weight=5, opacity=0.8).add_to(m)
            m.save("mapa_intermunicipal.html")
            webbrowser.open('file://' + os.path.realpath("mapa_intermunicipal.html"))