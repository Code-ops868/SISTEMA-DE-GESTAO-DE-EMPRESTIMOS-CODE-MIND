from django.core.management.base import BaseCommand
from microcredito_app.models import Provincia, Cidade, Distrito

class Command(BaseCommand):
    help = 'Popula o banco de dados com províncias, cidades e distritos de Moçambique'

    def handle(self, *args, **options):
        
        dados = {
            'Maputo': {
                'cidades': ['Maputo', 'Matola', 'Boane'],
                'distritos': ['Maputo', 'Matola', 'Boane', 'Marracuene', 'Manhiça', 'Namaacha', 'Moamba', 'Magude']
            },
            'Maputo Província': {
                'cidades': ['Matola'],
                'distritos': ['Matola', 'Boane', 'Magude', 'Manhiça', 'Marracuene', 'Moamba', 'Namaacha']
            },
            'Gaza': {
                'cidades': ['Xai-Xai', 'Chibuto'],
                'distritos': ['Xai-Xai', 'Chibuto', 'Bilene', 'Chicualacuala', 'Chokwe', 'Guijá', 'Limpopo', 'Mabalane', 'Manjacaze', 'Massangena', 'Massingir']
            },
            'Inhambane': {
                'cidades': ['Inhambane', 'Maxixe'],
                'distritos': ['Inhambane', 'Maxixe', 'Funhalouro', 'Govuro', 'Homoíne', 'Jangamo', 'Mabote', 'Massinga', 'Morrumbene', 'Panda', 'Vilanculos', 'Zavala']
            },
            'Sofala': {
                'cidades': ['Beira', 'Dondo'],
                'distritos': ['Beira', 'Dondo', 'Búzi', 'Caia', 'Chemba', 'Chibabava', 'Gorongosa', 'Machanga', 'Maringué', 'Marromeu', 'Muanza', 'Nhamatanda']
            },
            'Manica': {
                'cidades': ['Chimoio'],
                'distritos': ['Chimoio', 'Báruè', 'Gondola', 'Guro', 'Machaze', 'Macossa', 'Manica', 'Mossurize', 'Sussundenga', 'Tambara', 'Vanduzi']
            },
            'Tete': {
                'cidades': ['Tete'],
                'distritos': ['Tete', 'Angónia', 'Cahora-Bassa', 'Changara', 'Chifunde', 'Chiuta', 'Macanga', 'Magoé', 'Marávia', 'Moatize', 'Mutarara', 'Tsangano', 'Zumbo']
            },
            'Zambezia': {
                'cidades': ['Quelimane'],
                'distritos': ['Quelimane', 'Alto Molócuè', 'Chinde', 'Gilé', 'Gurúè', 'Ile', 'Inhassunge', 'Lugela', 'Maganja da Costa', 'Milange', 'Mocuba', 'Mocubela', 'Molumbo', 'Mopeia', 'Morrumbala', 'Namacurra', 'Namarroi', 'Nicoadala', 'Pebane']
            },
            'Nampula': {
                'cidades': ['Nampula', 'Nacala'],
                'distritos': ['Nampula', 'Nacala', 'Angoche', 'Eráti', 'Ilha de Moçambique', 'Lalaua', 'Malema', 'Meconta', 'Mecubúri', 'Memba', 'Mogincual', 'Mogovolas', 'Moma', 'Monapo', 'Mossuril', 'Muecate', 'Murrupula', 'Nacala-a-Velha', 'Nacarôa', 'Rapale', 'Ribaué']
            },
            'Cabo Delgado': {
                'cidades': ['Pemba'],
                'distritos': ['Pemba', 'Ancuabe', 'Balama', 'Chiúre', 'Ibo', 'Macomia', 'Mecúfi', 'Meluco', 'Mocímboa da Praia', 'Montepuez', 'Mueda', 'Muidumbe', 'Namuno', 'Nangade', 'Palma', 'Quissanga']
            },
            'Niassa': {
                'cidades': ['Lichinga'],
                'distritos': ['Lichinga', 'Cuamba', 'Lago', 'Majune', 'Mandimba', 'Marrupa', 'Maúa', 'Mavago', 'Mecanhelas', 'Mecula', 'Metarica', 'Muembe', 'Nipepe', 'Sanga']
            }
        }

        for provincia_nome, info in dados.items():
            provincia, created = Provincia.objects.get_or_create(nome=provincia_nome)
            
            for cidade_nome in info['cidades']:
                Cidade.objects.get_or_create(provincia=provincia, nome=cidade_nome)
            
            for distrito_nome in info['distritos']:
                Distrito.objects.get_or_create(provincia=provincia, nome=distrito_nome)
            
            self.stdout.write(self.style.SUCCESS(f'✅ {provincia_nome} processada'))

        self.stdout.write(self.style.SUCCESS('🎉 Dados carregados com sucesso!'))