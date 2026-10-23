import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Estado } from './estado';

describe('Estado', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Estado],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('muestra db: true cuando el backend responde', async () => {
    const fixture = TestBed.createComponent(Estado);
    fixture.detectChanges();
    http.expectOne('/api/health/').flush({ ok: true, db: true });
    await fixture.whenStable();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('db: true');
  });

  it('muestra un error legible si el servidor no responde', async () => {
    const fixture = TestBed.createComponent(Estado);
    fixture.detectChanges();
    http.expectOne('/api/health/').error(new ProgressEvent('error'));
    await fixture.whenStable();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No se pudo contactar al servidor.');
  });
});
