/**
 * Translate Japanese power grid terms to English for display.
 * Applied to all substation and line names from Japan grid data, for every location.
 * Covers prefectures, regions, power companies, and technical terms.
 */
const JP_TO_EN: Record<string, string> = {
  // Power companies (longer first)
  北海道電力: 'Hokkaido Electric',
  東北電力: 'Tohoku Electric',
  東京電力: 'Tokyo Electric',
  北陸電力: 'Hokuriku Electric',
  中部電力: 'Chubu Electric',
  関西電力: 'Kansai Electric',
  中国電力: 'Chugoku Electric',
  四国電力: 'Shikoku Electric',
  九州電力: 'Kyushu Electric',
  送配電: 'Transmission & Distribution',
  送電系統: 'Transmission System',
  送電系統図: 'Transmission Diagram',
  北陸エリア: 'Hokuriku Area',
  中部北陸: 'Chubu Hokuriku',
  // Compound place/station names
  山方変電所: 'Yamagata Substation',
  山方線: 'Yamagata Line',
  // Regions
  東京: 'Tokyo',
  茨城: 'Ibaraki',
  山方: 'Yamagata',
  山形: 'Yamagata',
  北海道: 'Hokkaido',
  東北: 'Tohoku',
  関東: 'Kanto',
  北陸: 'Hokuriku',
  中部: 'Chubu',
  関西: 'Kansai',
  中国: 'Chugoku',
  四国: 'Shikoku',
  九州: 'Kyushu',
  群馬: 'Gunma',
  埼玉: 'Saitama',
  千葉: 'Chiba',
  神奈川: 'Kanagawa',
  栃木: 'Tochigi',
  福島: 'Fukushima',
  新潟: 'Niigata',
  富山: 'Toyama',
  石川: 'Ishikawa',
  福井: 'Fukui',
  長野: 'Nagano',
  岐阜: 'Gifu',
  静岡: 'Shizuoka',
  愛知: 'Aichi',
  三重: 'Mie',
  滋賀: 'Shiga',
  京都: 'Kyoto',
  大阪: 'Osaka',
  兵庫: 'Hyogo',
  奈良: 'Nara',
  和歌山: 'Wakayama',
  鳥取: 'Tottori',
  島根: 'Shimane',
  岡山: 'Okayama',
  広島: 'Hiroshima',
  山口: 'Yamaguchi',
  徳島: 'Tokushima',
  香川: 'Kagawa',
  愛媛: 'Ehime',
  高知: 'Kochi',
  福岡: 'Fukuoka',
  佐賀: 'Saga',
  長崎: 'Nagasaki',
  熊本: 'Kumamoto',
  大分: 'Oita',
  宮崎: 'Miyazaki',
  鹿児島: 'Kagoshima',
  // Technical terms
  変電所: 'Substation',
  開閉所: 'Switching Station',
  発電所: 'Power Plant',
  送電線: 'Transmission Line',
  送電: 'Transmission',
  配電: 'Distribution',
  線: 'Line',
  以下: ' or below',
  以上: 'and above',
  基幹: 'Trunk',
  システム: 'System',
  架空線: 'Overhead Line',
  需要家: 'Consumer',
  大型: 'Large-scale',
  大口: 'High-volume',
  連絡: 'Interconnection',
  地域: 'Regional',
  供給: 'Supply',
  設備: 'Facility',
  事業者: 'Operator',
  保有: 'Owned',
  電力: 'Electric Power',
  ネットワーク: 'Network',
  図: 'Diagram',
  認定: 'Certified',
  施設: 'Facility',
  他所: 'Other',
  流動: 'Flow',
  所要: 'Required',
};

export function translateGridTerm(term: string): string {
  return JP_TO_EN[term] ?? term;
}

/**
 * Translate a Japanese grid name (substation/line) to readable English.
 * Applied to every substation and line name from grid connectivity results,
 * for all locations (Hokkaido, Tokyo, Kansai, Kyushu, etc.).
 */
export function translateGridName(name: string | null | undefined): string {
  if (!name || typeof name !== 'string') return '';
  const s = name.trim();
  if (!s) return '';
  // Replace known terms (longer matches first)
  const sorted = Object.entries(JP_TO_EN).sort((a, b) => b[0].length - a[0].length);
  let result = s;
  for (const [jp, en] of sorted) {
    result = result.split(jp).join(en);
  }
  // Replace remaining underscores between voltage/numbers with " "
  return result.replace(/_/g, ' ');
}
