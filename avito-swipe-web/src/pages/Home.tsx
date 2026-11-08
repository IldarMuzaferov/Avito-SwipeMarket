import { Link } from 'react-router-dom';
import { SwipeIcon } from '../components/Icons';
import { gradientFor } from '../lib/utils';

const TILES: [string, string][] = [
  ['Авто', '#e3f1ff'], ['Недвижимость', '#fff1d6'], ['Жильё для путешествий', '#e6f6dd'], ['Для дома и дачи', '#ffe6e0'], ['Запчасти', '#ece6ff'],
  ['Услуги', '#dff5f3'], ['Электроника', '#e3f1ff'], ['Работа и подработка', '#fff1d6'], ['Бизнес 360', '#e6f6dd'], ['Одежда, обувь, аксессуары', '#ffe6e0'],
];

export default function Home() {
  return (
    <div className="container home">
      <div className="top-links">
        <div>
          <span>Для бизнеса</span><span>Карьера в Авито</span><span>Помощь</span><span>Каталоги</span><span>#яПомогаю</span>
        </div>
        <div><span>Вход и регистрация</span><span>Разместить объявление</span></div>
      </div>

      <div className="home-grid">
        <div className="tiles">
          {TILES.map(([name, bg]) => (
            <div className="tile" key={name} style={{ background: bg }}>
              <b>{name}</b>
              <i />
            </div>
          ))}
        </div>
        <div className="biz">
          <h3>Всё для бизнеса</h3>
          <div className="biz-icons">
            {['Оборудование', 'Помещения', 'Товары'].map((t) => (
              <div key={t}><i />{t}</div>
            ))}
          </div>
          <button className="btn btn-secondary">Искать в Бизнес 360</button>
        </div>
      </div>

      <Link to="/swipe" className="swipe-promo">
        <SwipeIcon size={28} />
        <div>
          <b>Свайп — листайте товары как рилсы</b>
          <span>Свайпайте вправо, собирайте вишлист и делитесь им с друзьями</span>
        </div>
        <em>Попробовать</em>
      </Link>

      <div className="ads">
        {[0, 1, 2, 3, 4].map((i) => (
          <div className="ad" key={i}>
            <div className="ad-img" style={{ background: gradientFor(`ad${i}`) }} />
            {i === 4 && <span className="ad-badge">Хватамба</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
